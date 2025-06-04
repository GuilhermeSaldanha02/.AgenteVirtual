# -*- coding: utf-8 -*-
import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

# Modelos para o sistema de IA e advertências automatizadas
class OccurrencePattern(Base):
    __tablename__ = 'occurrence_pattern'
    
    id = Column(Integer, primary_key=True)
    pattern_type = Column(String(50), nullable=False)  # sazonal, localização, tipo
    description = Column(Text, nullable=False)
    confidence = Column(Float, default=0.0)
    discovery_date = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    predictions = relationship("OccurrencePrediction", back_populates="pattern", cascade="all, delete-orphan")

class OccurrencePrediction(Base):
    __tablename__ = 'occurrence_prediction'
    
    id = Column(Integer, primary_key=True)
    pattern_id = Column(Integer, ForeignKey('occurrence_pattern.id'), nullable=False)
    prediction_type = Column(String(50), nullable=False)
    predicted_date_start = Column(DateTime)
    predicted_date_end = Column(DateTime)
    location = Column(String(100))
    occurrence_type = Column(String(100))
    probability = Column(Float, default=0.0)
    status = Column(String(20), default='ativa')  # ativa, expirada, confirmada
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    pattern = relationship("OccurrencePattern", back_populates="predictions")
    automated_warnings = relationship("AutomatedWarning", back_populates="prediction")
    preventive_alerts = relationship("PreventiveAlert", back_populates="prediction")
    measure_mappings = relationship("PredictionMeasureMapping", back_populates="prediction")

class PreventiveMeasure(Base):
    __tablename__ = 'preventive_measure'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    applicability = Column(Text)
    effectiveness_rating = Column(Integer, default=0)  # 0-10
    implementation_difficulty = Column(Integer, default=0)  # 0-10
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    measure_mappings = relationship("PredictionMeasureMapping", back_populates="measure")

class PredictionMeasureMapping(Base):
    __tablename__ = 'prediction_measure_mapping'
    
    id = Column(Integer, primary_key=True)
    prediction_id = Column(Integer, ForeignKey('occurrence_prediction.id'), nullable=False)
    measure_id = Column(Integer, ForeignKey('preventive_measure.id'), nullable=False)
    relevance_score = Column(Integer, default=0)  # 0-10
    suggested_date = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    prediction = relationship("OccurrencePrediction", back_populates="measure_mappings")
    measure = relationship("PreventiveMeasure", back_populates="measure_mappings")

class PreventiveAlert(Base):
    __tablename__ = 'preventive_alert'
    
    id = Column(Integer, primary_key=True)
    prediction_id = Column(Integer, ForeignKey('occurrence_prediction.id'), nullable=False)
    alert_level = Column(String(20), nullable=False)  # baixo, médio, alto
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime)
    recipients = Column(Text)  # JSON string de destinatários
    status = Column(String(20), default='pendente')  # pendente, enviado, lido
    
    # Relacionamentos
    prediction = relationship("OccurrencePrediction", back_populates="preventive_alerts")

class AutomatedWarningRule(Base):
    __tablename__ = 'automated_warning_rule'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    trigger_type = Column(String(50), nullable=False)  # previsão, padrão, limiar
    trigger_condition = Column(String(255), nullable=False)
    trigger_value = Column(String(255), nullable=False)
    warning_template_id = Column(Integer)  # Referência ao template de advertência
    auto_send = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer)  # Referência ao usuário
    
    # Relacionamentos
    automated_warnings = relationship("AutomatedWarning", back_populates="rule")

class AutomatedWarning(Base):
    __tablename__ = 'automated_warning'
    
    id = Column(Integer, primary_key=True)
    rule_id = Column(Integer, ForeignKey('automated_warning_rule.id'), nullable=False)
    prediction_id = Column(Integer, ForeignKey('occurrence_prediction.id'))
    generation_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default='pendente')  # pendente, aprovada, enviada, cancelada
    approval_user_id = Column(Integer)  # Referência ao usuário
    approval_date = Column(DateTime)
    target_units = Column(Text)  # JSON string de unidades alvo
    warning_content = Column(Text)
    sent_date = Column(DateTime)
    
    # Relacionamentos
    rule = relationship("AutomatedWarningRule", back_populates="automated_warnings")
    prediction = relationship("OccurrencePrediction", back_populates="automated_warnings")

# Classe para gerenciar o sistema de IA e advertências automatizadas
class AIWarningManager:
    def __init__(self, db_session):
        self.db_session = db_session
        self.model = None
        self.scaler = None
    
    def train_prediction_model(self, historical_data=None):
        """Treina o modelo de previsão com dados históricos"""
        # Se não forem fornecidos dados históricos, buscar do banco de dados
        if historical_data is None:
            # Aqui seria a lógica para buscar ocorrências históricas
            # Por simplicidade, vamos criar dados de exemplo
            from models import Occurrence
            occurrences = self.db_session.query(Occurrence).all()
            
            if not occurrences:
                print("Sem dados históricos suficientes para treinar o modelo")
                return False
            
            # Preparar dados para treinamento
            data = []
            for occurrence in occurrences:
                # Extrair características relevantes
                weekday = occurrence.created_at.weekday()
                month = occurrence.created_at.month
                hour = occurrence.created_at.hour
                
                # Extrair informações da unidade
                unit_number = int(occurrence.unit_number) if occurrence.unit_number and occurrence.unit_number.isdigit() else 0
                
                # Extrair tipo de ocorrência (simplificado)
                occurrence_type = self._categorize_occurrence_type(occurrence.title, occurrence.description)
                
                data.append({
                    'weekday': weekday,
                    'month': month,
                    'hour': hour,
                    'unit_number': unit_number,
                    'occurrence_type': occurrence_type
                })
            
            historical_data = pd.DataFrame(data)
        
        # Verificar se há dados suficientes
        if len(historical_data) < 10:  # Número mínimo arbitrário
            print("Dados insuficientes para treinamento efetivo")
            return False
        
        # Preparar features e target
        X = historical_data.drop('occurrence_type', axis=1)
        y = historical_data['occurrence_type']
        
        # Normalizar dados
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Dividir em treino e teste
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
        
        # Treinar modelo
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)
        
        # Avaliar modelo
        accuracy = self.model.score(X_test, y_test)
        print(f"Modelo treinado com acurácia: {accuracy:.2f}")
        
        return True
    
    def _categorize_occurrence_type(self, title, description):
        """Categoriza o tipo de ocorrência com base no título e descrição"""
        text = (title + " " + description).lower()
        
        categories = {
            'barulho': ['barulho', 'som', 'ruído', 'música', 'festa'],
            'obras': ['obra', 'reforma', 'construção', 'manutenção'],
            'animais': ['animal', 'cachorro', 'gato', 'pet', 'latido'],
            'estacionamento': ['estacionamento', 'vaga', 'garagem', 'veículo', 'carro'],
            'áreas_comuns': ['área comum', 'piscina', 'salão', 'playground', 'academia'],
            'segurança': ['segurança', 'incêndio', 'emergência', 'acidente'],
            'lixo': ['lixo', 'resíduo', 'descarte', 'sujeira']
        }
        
        for category, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        return 'outros'
    
    def analyze_patterns(self):
        """Analisa os dados históricos para identificar padrões"""
        from models import Occurrence
        occurrences = self.db_session.query(Occurrence).all()
        
        if not occurrences:
            return []
        
        # Análise de padrões sazonais
        weekday_counts = {}
        month_counts = {}
        hour_counts = {}
        location_counts = {}
        type_counts = {}
        
        for occurrence in occurrences:
            # Contagem por dia da semana
            weekday = occurrence.created_at.weekday()
            weekday_counts[weekday] = weekday_counts.get(weekday, 0) + 1
            
            # Contagem por mês
            month = occurrence.created_at.month
            month_counts[month] = month_counts.get(month, 0) + 1
            
            # Contagem por hora
            hour = occurrence.created_at.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
            
            # Contagem por localização (unidade)
            location = occurrence.unit_number
            location_counts[location] = location_counts.get(location, 0) + 1
            
            # Contagem por tipo
            occurrence_type = self._categorize_occurrence_type(occurrence.title, occurrence.description)
            type_counts[occurrence_type] = type_counts.get(occurrence_type, 0) + 1
        
        # Identificar padrões significativos
        patterns = []
        
        # Padrão de dia da semana
        if weekday_counts:
            max_weekday = max(weekday_counts, key=weekday_counts.get)
            weekday_names = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
            total_occurrences = sum(weekday_counts.values())
            weekday_percentage = (weekday_counts[max_weekday] / total_occurrences) * 100
            
            if weekday_percentage > 25:  # Limiar arbitrário
                pattern = OccurrencePattern(
                    pattern_type='sazonal',
                    description=f"Concentração de ocorrências às {weekday_names[max_weekday]}s ({weekday_percentage:.1f}%)",
                    confidence=min(weekday_percentage / 100, 0.95)
                )
                self.db_session.add(pattern)
                patterns.append(pattern)
        
        # Padrão de mês
        if month_counts:
            max_month = max(month_counts, key=month_counts.get)
            month_names = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
                          'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
            total_occurrences = sum(month_counts.values())
            month_percentage = (month_counts[max_month] / total_occurrences) * 100
            
            if month_percentage > 15:  # Limiar arbitrário
                pattern = OccurrencePattern(
                    pattern_type='sazonal',
                    description=f"Concentração de ocorrências em {month_names[max_month-1]} ({month_percentage:.1f}%)",
                    confidence=min(month_percentage / 100, 0.9)
                )
                self.db_session.add(pattern)
                patterns.append(pattern)
        
        # Padrão de hora
        if hour_counts:
            max_hour = max(hour_counts, key=hour_counts.get)
            total_occurrences = sum(hour_counts.values())
            hour_percentage = (hour_counts[max_hour] / total_occurrences) * 100
            
            if hour_percentage > 20:  # Limiar arbitrário
                period = "manhã" if 6 <= max_hour < 12 else "tarde" if 12 <= max_hour < 18 else "noite"
                pattern = OccurrencePattern(
                    pattern_type='sazonal',
                    description=f"Concentração de ocorrências no período da {period} ({hour_percentage:.1f}%)",
                    confidence=min(hour_percentage / 100, 0.9)
                )
                self.db_session.add(pattern)
                patterns.append(pattern)
        
        # Padrão de localização
        if location_counts:
            max_location = max(location_counts, key=location_counts.get)
            total_occurrences = sum(location_counts.values())
            location_percentage = (location_counts[max_location] / total_occurrences) * 100
            
            if location_percentage > 15:  # Limiar arbitrário
                pattern = OccurrencePattern(
                    pattern_type='localização',
                    description=f"Concentração de ocorrências na unidade {max_location} ({location_percentage:.1f}%)",
                    confidence=min(location_percentage / 100, 0.85)
                )
                self.db_session.add(pattern)
                patterns.append(pattern)
        
        # Padrão de tipo
        if type_counts:
            max_type = max(type_counts, key=type_counts.get)
            total_occurrences = sum(type_counts.values())
            type_percentage = (type_counts[max_type] / total_occurrences) * 100
            
            if type_percentage > 30:  # Limiar arbitrário
                pattern = OccurrencePattern(
                    pattern_type='tipo',
                    description=f"Predominância de ocorrências do tipo '{max_type}' ({type_percentage:.1f}%)",
                    confidence=min(type_percentage / 100, 0.9)
                )
                self.db_session.add(pattern)
                patterns.append(pattern)
        
        # Salvar padrões no banco de dados
        self.db_session.commit()
        
        return patterns
    
    def generate_predictions(self):
        """Gera previsões baseadas nos padrões identificados"""
        # Buscar padrões ativos
        patterns = self.db_session.query(OccurrencePattern).all()
        
        if not patterns:
            return []
        
        predictions = []
        
        for pattern in patterns:
            # Diferentes estratégias de previsão baseadas no tipo de padrão
            if pattern.pattern_type == 'sazonal':
                if 'Segunda' in pattern.description or 'Terça' in pattern.description or 'Quarta' in pattern.description or \
                   'Quinta' in pattern.description or 'Sexta' in pattern.description or 'Sábado' in pattern.description or \
                   'Domingo' in pattern.description:
                    # Padrão de dia da semana
                    weekday_map = {'Segunda': 0, 'Terça': 1, 'Quarta': 2, 'Quinta': 3, 'Sexta': 4, 'Sábado': 5, 'Domingo': 6}
                    for day_name, day_num in weekday_map.items():
                        if day_name in pattern.description:
                            # Prever próximas 4 ocorrências deste dia da semana
                            for i in range(1, 5):
                                # Calcular próxima data com este dia da semana
                                today = datetime.utcnow().date()
                                days_ahead = (day_num - today.weekday()) % 7
                                if days_ahead == 0:
                                    days_ahead = 7  # Se for hoje, pular para próxima semana
                                next_date = today + timedelta(days=days_ahead + (i-1)*7)
                                
                                prediction = OccurrencePrediction(
                                    pattern_id=pattern.id,
                                    prediction_type='sazonal',
                                    predicted_date_start=datetime.combine(next_date, datetime.min.time()),
                                    predicted_date_end=datetime.combine(next_date, datetime.max.time()),
                                    probability=pattern.confidence * (1 - (i-1)*0.1)  # Diminui confiança para datas mais distantes
                                )
                                self.db_session.add(prediction)
                                predictions.append(prediction)
                
                elif 'Janeiro' in pattern.description or 'Fevereiro' in pattern.description or 'Março' in pattern.description or \
                     'Abril' in pattern.description or 'Maio' in pattern.description or 'Junho' in pattern.description or \
                     'Julho' in pattern.description or 'Agosto' in pattern.description or 'Setembro' in pattern.description or \
                     'Outubro' in pattern.description or 'Novembro' in pattern.description or 'Dezembro' in pattern.description:
                    # Padrão de mês
                    month_map = {'Janeiro': 1, 'Fevereiro': 2, 'Março': 3, 'Abril': 4, 'Maio': 5, 'Junho': 6,
                                'Julho': 7, 'Agosto': 8, 'Setembro': 9, 'Outubro': 10, 'Novembro': 11, 'Dezembro': 12}
                    for month_name, month_num in month_map.items():
                        if month_name in pattern.description:
                            # Prever próxima ocorrência neste mês
                            today = datetime.utcnow().date()
                            current_year = today.year
                            next_year = current_year if today.month <= month_num else current_year + 1
                            
                            start_date = datetime(next_year, month_num, 1)
                            end_date = datetime(next_year, month_num + 1, 1) if month_num < 12 else datetime(next_year + 1, 1, 1)
                            end_date = end_date - timedelta(days=1)
                            
                            prediction = OccurrencePrediction(
                                pattern_id=pattern.id,
                                prediction_type='sazonal',
                                predicted_date_start=start_date,
                                predicted_date_end=end_date,
                                probability=pattern.confidence
                            )
                            self.db_session.add(prediction)
                            predictions.append(prediction)
                
                elif 'manhã' in pattern.description or 'tarde' in pattern.description or 'noite' in pattern.description:
                    # Padrão de período do dia
                    period_map = {'manhã': (6, 12), 'tarde': (12, 18), 'noite': (18, 6)}
                    for period_name, (start_hour, end_hour) in period_map.items():
                        if period_name in pattern.description:
                            # Prever próximos 7 dias neste período
                            for i in range(1, 8):
                                next_date = datetime.utcnow().date() + timedelta(days=i)
                                
                                if end_hour > start_hour:
                                    start_time = datetime.combine(next_date, datetime.min.time().replace(hour=start_hour))
                                    end_time = datetime.combine(next_date, datetime.min.time().replace(hour=end_hour))
                                else:
                                    # Período noturno que cruza a meia-noite
                                    start_time = datetime.combine(next_date, datetime.min.time().replace(hour=start_hour))
                                    end_time = datetime.combine(next_date + timedelta(days=1), datetime.min.time().replace(hour=end_hour))
                                
                                prediction = OccurrencePrediction(
                                    pattern_id=pattern.id,
                                    prediction_type='sazonal',
                                    predicted_date_start=start_time,
                                    predicted_date_end=end_time,
                                    probability=pattern.confidence * (1 - (i-1)*0.05)  # Diminui confiança para datas mais distantes
                                )
                                self.db_session.add(prediction)
                                predictions.append(prediction)
            
            elif pattern.pattern_type == 'localização':
                # Extrair unidade da descrição
                import re
                unit_match = re.search(r'unidade (\w+)', pattern.description)
                if unit_match:
                    unit = unit_match.group(1)
                    
                    # Prever próximos 30 dias para esta unidade
                    for i in range(1, 31):
                        next_date = datetime.utcnow().date() + timedelta(days=i)
                        
                        prediction = OccurrencePrediction(
                            pattern_id=pattern.id,
                            prediction_type='localização',
                            predicted_date_start=datetime.combine(next_date, datetime.min.time()),
                            predicted_date_end=datetime.combine(next_date, datetime.max.time()),
                            location=unit,
                            probability=pattern.confidence * (1 - (i-1)*0.02)  # Diminui confiança para datas mais distantes
                        )
                        self.db_session.add(prediction)
                        predictions.append(prediction)
            
            elif pattern.pattern_type == 'tipo':
                # Extrair tipo da descrição
                import re
                type_match = re.search(r"tipo '(\w+)'", pattern.description)
                if type_match:
                    occurrence_type = type_match.group(1)
                    
                    # Prever próximos 14 dias para este tipo
                    for i in range(1, 15):
                        next_date = datetime.utcnow().date() + timedelta(days=i)
                        
                        prediction = OccurrencePrediction(
                            pattern_id=pattern.id,
                            prediction_type='tipo',
                            predicted_date_start=datetime.combine(next_date, datetime.min.time()),
                            predicted_date_end=datetime.combine(next_date, datetime.max.time()),
                            occurrence_type=occurrence_type,
                            probability=pattern.confidence * (1 - (i-1)*0.03)  # Diminui confiança para datas mais distantes
                        )
                        self.db_session.add(prediction)
                        predictions.append(prediction)
        
        # Salvar previsões no banco de dados
        self.db_session.commit()
        
        return predictions
    
    def generate_preventive_measures(self, prediction_id=None):
        """Gera medidas preventivas para previsões"""
        # Buscar previsões ativas
        query = self.db_session.query(OccurrencePrediction).filter(OccurrencePrediction.status == 'ativa')
        if prediction_id:
            query = query.filter(OccurrencePrediction.id == prediction_id)
        
        predictions = query.all()
        
        if not predictions:
            return []
        
        # Catálogo de medidas preventivas por tipo
        preventive_catalog = {
            'barulho': [
                {
                    'title': 'Comunicado sobre horários de silêncio',
                    'description': 'Enviar comunicado relembrando os horários de silêncio conforme regimento interno.',
                    'effectiveness': 7,
                    'difficulty': 2
                },
                {
                    'title': 'Inspeção acústica preventiva',
                    'description': 'Realizar inspeção acústica nas áreas comuns e unidades com histórico de reclamações.',
                    'effectiveness': 8,
                    'difficulty': 6
                }
            ],
            'obras': [
                {
                    'title': 'Comunicado sobre horários de obras',
                    'description': 'Enviar comunicado relembrando os horários permitidos para obras conforme regimento interno.',
                    'effectiveness': 7,
                    'difficulty': 2
                },
                {
                    'title': 'Vistoria preventiva',
                    'description': 'Realizar vistoria nas unidades com obras em andamento para verificar conformidade.',
                    'effectiveness': 9,
                    'difficulty': 7
                }
            ],
            'animais': [
                {
                    'title': 'Comunicado sobre regras para animais',
                    'description': 'Enviar comunicado relembrando as regras para criação de animais no condomínio.',
                    'effectiveness': 6,
                    'difficulty': 2
                },
                {
                    'title': 'Campanha de conscientização',
                    'description': 'Realizar campanha de conscientização sobre cuidados com animais de estimação em condomínios.',
                    'effectiveness': 8,
                    'difficulty': 5
                }
            ],
            'estacionamento': [
                {
                    'title': 'Verificação de vagas',
                    'description': 'Realizar verificação das vagas de estacionamento para identificar uso irregular.',
                    'effectiveness': 8,
                    'difficulty': 4
                },
                {
                    'title': 'Comunicado sobre regras de estacionamento',
                    'description': 'Enviar comunicado relembrando as regras de uso das vagas de estacionamento.',
                    'effectiveness': 6,
                    'difficulty': 2
                }
            ],
            'áreas_comuns': [
                {
                    'title': 'Inspeção das áreas comuns',
                    'description': 'Realizar inspeção preventiva nas áreas comuns para identificar possíveis problemas.',
                    'effectiveness': 8,
                    'difficulty': 5
                },
                {
                    'title': 'Comunicado sobre uso de áreas comuns',
                    'description': 'Enviar comunicado relembrando as regras de uso das áreas comuns do condomínio.',
                    'effectiveness': 7,
                    'difficulty': 2
                }
            ],
            'segurança': [
                {
                    'title': 'Verificação de equipamentos de segurança',
                    'description': 'Realizar verificação dos equipamentos de segurança (câmeras, alarmes, etc.).',
                    'effectiveness': 9,
                    'difficulty': 6
                },
                {
                    'title': 'Comunicado sobre procedimentos de segurança',
                    'description': 'Enviar comunicado sobre procedimentos de segurança e prevenção de acidentes.',
                    'effectiveness': 7,
                    'difficulty': 3
                }
            ],
            'lixo': [
                {
                    'title': 'Inspeção das áreas de descarte',
                    'description': 'Realizar inspeção preventiva nas áreas de descarte de lixo e recicláveis.',
                    'effectiveness': 8,
                    'difficulty': 4
                },
                {
                    'title': 'Comunicado sobre descarte correto',
                    'description': 'Enviar comunicado sobre procedimentos corretos para descarte de lixo e recicláveis.',
                    'effectiveness': 7,
                    'difficulty': 2
                }
            ],
            'outros': [
                {
                    'title': 'Reunião preventiva com síndico',
                    'description': 'Realizar reunião com síndico para discutir medidas preventivas gerais.',
                    'effectiveness': 8,
                    'difficulty': 5
                },
                {
                    'title': 'Comunicado geral sobre regimento',
                    'description': 'Enviar comunicado geral relembrando pontos importantes do regimento interno.',
                    'effectiveness': 6,
                    'difficulty': 3
                }
            ]
        }
        
        # Medidas gerais para todos os tipos
        general_measures = [
            {
                'title': 'Reforço na comunicação do regimento',
                'description': 'Enviar cópia do regimento interno com destaque para os artigos mais relevantes.',
                'effectiveness': 6,
                'difficulty': 3
            },
            {
                'title': 'Presença intensificada de funcionários',
                'description': 'Aumentar a presença de funcionários nas áreas e horários com maior probabilidade de ocorrências.',
                'effectiveness': 7,
                'difficulty': 6
            }
        ]
        
        mappings = []
        
        for prediction in predictions:
            # Determinar tipo de ocorrência prevista
            occurrence_type = prediction.occurrence_type or 'outros'
            
            # Selecionar medidas específicas para o tipo
            specific_measures = preventive_catalog.get(occurrence_type, preventive_catalog['outros'])
            
            # Combinar com medidas gerais
            all_measures = specific_measures + general_measures
            
            for measure_data in all_measures:
                # Verificar se a medida já existe
                measure = self.db_session.query(PreventiveMeasure).filter_by(
                    title=measure_data['title']
                ).first()
                
                # Se não existir, criar
                if not measure:
                    measure = PreventiveMeasure(
                        title=measure_data['title'],
                        description=measure_data['description'],
                        effectiveness_rating=measure_data.get('effectiveness', 5),
                        implementation_difficulty=measure_data.get('difficulty', 5)
                    )
                    self.db_session.add(measure)
                    self.db_session.flush()  # Para obter o ID
                
                # Criar mapeamento entre previsão e medida
                mapping = PredictionMeasureMapping(
                    prediction_id=prediction.id,
                    measure_id=measure.id,
                    relevance_score=min(10, int(prediction.probability * 10) + measure.effectiveness_rating - measure.implementation_difficulty)
                )
                self.db_session.add(mapping)
                mappings.append(mapping)
        
        # Salvar no banco de dados
        self.db_session.commit()
        
        return mappings
    
    def generate_preventive_alerts(self, prediction_id=None, min_probability=0.6):
        """Gera alertas preventivos para previsões com alta probabilidade"""
        # Buscar previsões ativas com probabilidade acima do limiar
        query = self.db_session.query(OccurrencePrediction).filter(
            OccurrencePrediction.status == 'ativa',
            OccurrencePrediction.probability >= min_probability
        )
        
        if prediction_id:
            query = query.filter(OccurrencePrediction.id == prediction_id)
        
        predictions = query.all()
        
        if not predictions:
            return []
        
        alerts = []
        
        for prediction in predictions:
            # Determinar nível de alerta baseado na probabilidade
            if prediction.probability >= 0.8:
                alert_level = 'alto'
            elif prediction.probability >= 0.7:
                alert_level = 'médio'
            else:
                alert_level = 'baixo'
            
            # Criar título e mensagem baseados no tipo de previsão
            if prediction.prediction_type == 'sazonal':
                title = f"Alerta Preventivo: Possível ocorrência em {prediction.predicted_date_start.strftime('%d/%m/%Y')}"
                
                if prediction.predicted_date_start and prediction.predicted_date_end and \
                   prediction.predicted_date_start.date() == prediction.predicted_date_end.date():
                    # Previsão para um dia específico
                    message = f"Nosso sistema de IA identificou uma possível ocorrência para o dia {prediction.predicted_date_start.strftime('%d/%m/%Y')}. "
                else:
                    # Previsão para um período
                    start_str = prediction.predicted_date_start.strftime('%d/%m/%Y') if prediction.predicted_date_start else "data não especificada"
                    end_str = prediction.predicted_date_end.strftime('%d/%m/%Y') if prediction.predicted_date_end else "data não especificada"
                    message = f"Nosso sistema de IA identificou uma possível ocorrência no período de {start_str} a {end_str}. "
            
            elif prediction.prediction_type == 'localização':
                title = f"Alerta Preventivo: Possível ocorrência na unidade {prediction.location}"
                message = f"Nosso sistema de IA identificou uma possível ocorrência relacionada à unidade {prediction.location}. "
            
            elif prediction.prediction_type == 'tipo':
                title = f"Alerta Preventivo: Possível ocorrência do tipo '{prediction.occurrence_type}'"
                message = f"Nosso sistema de IA identificou uma possível ocorrência do tipo '{prediction.occurrence_type}'. "
            
            else:
                title = "Alerta Preventivo: Possível ocorrência detectada"
                message = "Nosso sistema de IA identificou uma possível ocorrência. "
            
            # Adicionar informações sobre a probabilidade
            message += f"A probabilidade estimada é de {prediction.probability*100:.1f}%. "
            
            # Adicionar recomendações baseadas nas medidas preventivas
            mappings = self.db_session.query(PredictionMeasureMapping).filter_by(
                prediction_id=prediction.id
            ).order_by(PredictionMeasureMapping.relevance_score.desc()).limit(3).all()
            
            if mappings:
                message += "Recomendamos as seguintes medidas preventivas:\n\n"
                for i, mapping in enumerate(mappings, 1):
                    measure = self.db_session.query(PreventiveMeasure).filter_by(
                        id=mapping.measure_id
                    ).first()
                    
                    if measure:
                        message += f"{i}. {measure.title}: {measure.description}\n"
            
            # Criar alerta
            alert = PreventiveAlert(
                prediction_id=prediction.id,
                alert_level=alert_level,
                title=title,
                message=message,
                recipients=json.dumps(['admin', 'sindico'])  # Simplificado
            )
            self.db_session.add(alert)
            alerts.append(alert)
        
        # Salvar no banco de dados
        self.db_session.commit()
        
        return alerts
    
    def process_automated_warning_rules(self):
        """Processa regras de advertências automatizadas"""
        # Buscar regras ativas
        rules = self.db_session.query(AutomatedWarningRule).filter_by(is_active=True).all()
        
        if not rules:
            return []
        
        warnings = []
        
        for rule in rules:
            # Processar regra baseada no tipo de gatilho
            if rule.trigger_type == 'previsão':
                # Buscar previsões que atendem à condição
                predictions = self.db_session.query(OccurrencePrediction).filter(
                    OccurrencePrediction.status == 'ativa'
                ).all()
                
                for prediction in predictions:
                    # Verificar se a previsão atende à condição da regra
                    if self._check_prediction_condition(prediction, rule.trigger_condition, rule.trigger_value):
                        # Gerar advertência automatizada
                        warning = self._generate_automated_warning(rule, prediction)
                        warnings.append(warning)
            
            elif rule.trigger_type == 'padrão':
                # Buscar padrões que atendem à condição
                patterns = self.db_session.query(OccurrencePattern).all()
                
                for pattern in patterns:
                    # Verificar se o padrão atende à condição da regra
                    if self._check_pattern_condition(pattern, rule.trigger_condition, rule.trigger_value):
                        # Gerar advertência automatizada
                        warning = self._generate_automated_warning(rule, pattern=pattern)
                        warnings.append(warning)
            
            elif rule.trigger_type == 'limiar':
                # Implementação simplificada para limiares
                # Na prática, isso dependeria de contadores ou métricas específicas
                pass
        
        # Salvar no banco de dados
        self.db_session.commit()
        
        return warnings
    
    def _check_prediction_condition(self, prediction, condition, value):
        """Verifica se uma previsão atende a uma condição específica"""
        if condition == 'probabilidade_acima':
            return prediction.probability >= float(value)
        
        elif condition == 'tipo_ocorrencia':
            return prediction.occurrence_type == value
        
        elif condition == 'localizacao':
            return prediction.location == value
        
        elif condition == 'data_proxima':
            # Verificar se a data prevista está dentro dos próximos X dias
            days = int(value)
            if prediction.predicted_date_start:
                return (prediction.predicted_date_start.date() - datetime.utcnow().date()).days <= days
        
        return False
    
    def _check_pattern_condition(self, pattern, condition, value):
        """Verifica se um padrão atende a uma condição específica"""
        if condition == 'confianca_acima':
            return pattern.confidence >= float(value)
        
        elif condition == 'tipo_padrao':
            return pattern.pattern_type == value
        
        elif condition == 'descricao_contem':
            return value.lower() in pattern.description.lower()
        
        return False
    
    def _generate_automated_warning(self, rule, prediction=None, pattern=None):
        """Gera uma advertência automatizada baseada em uma regra"""
        # Determinar conteúdo da advertência
        if prediction:
            # Baseado na previsão
            content = self._generate_warning_content_from_prediction(prediction, rule.warning_template_id)
            target_units = self._determine_target_units_from_prediction(prediction)
        elif pattern:
            # Baseado no padrão
            content = self._generate_warning_content_from_pattern(pattern, rule.warning_template_id)
            target_units = self._determine_target_units_from_pattern(pattern)
        else:
            # Genérico
            content = self._generate_generic_warning_content(rule.warning_template_id)
            target_units = []
        
        # Criar advertência
        warning = AutomatedWarning(
            rule_id=rule.id,
            prediction_id=prediction.id if prediction else None,
            warning_content=content,
            target_units=json.dumps(target_units),
            status='aprovada' if rule.auto_send else 'pendente'
        )
        
        # Se for envio automático, definir data de envio
        if rule.auto_send:
            warning.sent_date = datetime.utcnow()
        
        self.db_session.add(warning)
        self.db_session.flush()  # Para obter o ID
        
        return warning
    
    def _generate_warning_content_from_prediction(self, prediction, template_id):
        """Gera conteúdo de advertência baseado em uma previsão"""
        # Simplificado - na prática, buscaria um template no banco de dados
        content = f"""
        <h2>Advertência Preventiva</h2>
        
        <p>Prezado(a) Condômino(a),</p>
        
        <p>Esta é uma advertência preventiva baseada em análise de dados históricos e previsões do nosso sistema de inteligência artificial.</p>
        
        <p>Identificamos um padrão de ocorrências que sugere uma possível infração relacionada a """
        
        if prediction.occurrence_type:
            content += f"<strong>{prediction.occurrence_type}</strong>"
        else:
            content += "regras do condomínio"
        
        if prediction.predicted_date_start:
            content += f" no período de <strong>{prediction.predicted_date_start.strftime('%d/%m/%Y')}</strong>"
            
            if prediction.predicted_date_end and prediction.predicted_date_end.date() != prediction.predicted_date_start.date():
                content += f" a <strong>{prediction.predicted_date_end.strftime('%d/%m/%Y')}</strong>"
        
        content += ".</p>"
        
        content += """
        <p>Solicitamos sua atenção às regras do condomínio para evitar possíveis transtornos e a necessidade de medidas mais severas.</p>
        
        <p>Esta advertência tem caráter preventivo e não implica em penalidades neste momento.</p>
        
        <p>Atenciosamente,<br>
        Administração do Condomínio</p>
        """
        
        return content
    
    def _generate_warning_content_from_pattern(self, pattern, template_id):
        """Gera conteúdo de advertência baseado em um padrão"""
        # Simplificado - na prática, buscaria um template no banco de dados
        content = f"""
        <h2>Advertência Preventiva</h2>
        
        <p>Prezado(a) Condômino(a),</p>
        
        <p>Esta é uma advertência preventiva baseada em análise de dados históricos do nosso sistema de inteligência artificial.</p>
        
        <p>Identificamos o seguinte padrão: <strong>{pattern.description}</strong></p>
        
        <p>Este padrão sugere possíveis infrações às regras do condomínio. Solicitamos sua atenção ao regimento interno para evitar possíveis transtornos e a necessidade de medidas mais severas.</p>
        
        <p>Esta advertência tem caráter preventivo e não implica em penalidades neste momento.</p>
        
        <p>Atenciosamente,<br>
        Administração do Condomínio</p>
        """
        
        return content
    
    def _generate_generic_warning_content(self, template_id):
        """Gera conteúdo genérico de advertência"""
        # Simplificado - na prática, buscaria um template no banco de dados
        content = """
        <h2>Advertência Preventiva</h2>
        
        <p>Prezado(a) Condômino(a),</p>
        
        <p>Esta é uma advertência preventiva baseada em análise de dados históricos do nosso sistema de inteligência artificial.</p>
        
        <p>Identificamos padrões que sugerem possíveis infrações às regras do condomínio. Solicitamos sua atenção ao regimento interno para evitar possíveis transtornos e a necessidade de medidas mais severas.</p>
        
        <p>Esta advertência tem caráter preventivo e não implica em penalidades neste momento.</p>
        
        <p>Atenciosamente,<br>
        Administração do Condomínio</p>
        """
        
        return content
    
    def _determine_target_units_from_prediction(self, prediction):
        """Determina unidades alvo com base em uma previsão"""
        if prediction.location:
            # Se a previsão tem localização específica
            return [prediction.location]
        
        # Caso contrário, simplificado para exemplo
        # Na prática, poderia usar dados históricos para determinar unidades relevantes
        return []
    
    def _determine_target_units_from_pattern(self, pattern):
        """Determina unidades alvo com base em um padrão"""
        if pattern.pattern_type == 'localização':
            # Extrair unidade da descrição
            import re
            unit_match = re.search(r'unidade (\w+)', pattern.description)
            if unit_match:
                return [unit_match.group(1)]
        
        # Caso contrário, simplificado para exemplo
        return []
    
    def approve_automated_warning(self, warning_id, user_id):
        """Aprova uma advertência automatizada pendente"""
        warning = self.db_session.query(AutomatedWarning).filter_by(
            id=warning_id,
            status='pendente'
        ).first()
        
        if not warning:
            return False
        
        warning.status = 'aprovada'
        warning.approval_user_id = user_id
        warning.approval_date = datetime.utcnow()
        
        self.db_session.commit()
        return True
    
    def send_automated_warning(self, warning_id):
        """Envia uma advertência automatizada aprovada"""
        warning = self.db_session.query(AutomatedWarning).filter_by(
            id=warning_id,
            status='aprovada'
        ).first()
        
        if not warning:
            return False
        
        # Lógica de envio (simplificada)
        # Na prática, integraria com o sistema de e-mail
        
        warning.status = 'enviada'
        warning.sent_date = datetime.utcnow()
        
        self.db_session.commit()
        return True
    
    def cancel_automated_warning(self, warning_id, reason=None):
        """Cancela uma advertência automatizada"""
        warning = self.db_session.query(AutomatedWarning).filter_by(
            id=warning_id
        ).filter(AutomatedWarning.status.in_(['pendente', 'aprovada'])).first()
        
        if not warning:
            return False
        
        warning.status = 'cancelada'
        
        self.db_session.commit()
        return True
    
    def get_dashboard_data(self):
        """Obtém dados para o dashboard de IA"""
        # Contagem de padrões por tipo
        pattern_counts = {}
        patterns = self.db_session.query(OccurrencePattern).all()
        for pattern in patterns:
            pattern_counts[pattern.pattern_type] = pattern_counts.get(pattern.pattern_type, 0) + 1
        
        # Contagem de previsões por status
        prediction_status_counts = {}
        predictions = self.db_session.query(OccurrencePrediction).all()
        for prediction in predictions:
            prediction_status_counts[prediction.status] = prediction_status_counts.get(prediction.status, 0) + 1
        
        # Contagem de advertências automatizadas por status
        warning_status_counts = {}
        warnings = self.db_session.query(AutomatedWarning).all()
        for warning in warnings:
            warning_status_counts[warning.status] = warning_status_counts.get(warning.status, 0) + 1
        
        # Previsões para os próximos 30 dias
        today = datetime.utcnow().date()
        upcoming_predictions = []
        for i in range(30):
            date = today + timedelta(days=i)
            count = self.db_session.query(OccurrencePrediction).filter(
                OccurrencePrediction.predicted_date_start <= datetime.combine(date, datetime.max.time()),
                OccurrencePrediction.predicted_date_end >= datetime.combine(date, datetime.min.time()),
                OccurrencePrediction.status == 'ativa'
            ).count()
            
            upcoming_predictions.append({
                'date': date.strftime('%Y-%m-%d'),
                'count': count
            })
        
        # Alertas recentes
        recent_alerts = []
        alerts = self.db_session.query(PreventiveAlert).order_by(PreventiveAlert.created_at.desc()).limit(5).all()
        for alert in alerts:
            recent_alerts.append({
                'id': alert.id,
                'title': alert.title,
                'level': alert.alert_level,
                'created_at': alert.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return {
            'pattern_counts': pattern_counts,
            'prediction_status_counts': prediction_status_counts,
            'warning_status_counts': warning_status_counts,
            'upcoming_predictions': upcoming_predictions,
            'recent_alerts': recent_alerts
        }

# Função para criar tabelas no banco de dados
def create_ai_warning_tables(engine):
    """Cria as tabelas necessárias para o sistema de IA e advertências automatizadas"""
    Base.metadata.create_all(engine)

# Rotas Flask para o sistema de IA e advertências automatizadas (a serem integradas ao app.py)
def register_ai_warning_routes(app, db):
    """Registra as rotas para o sistema de IA e advertências automatizadas"""
    ai_manager = AIWarningManager(db.session)
    
    @app.route('/ai/dashboard')
    @login_required
    def ai_dashboard():
        """Dashboard do sistema de IA"""
        dashboard_data = ai_manager.get_dashboard_data()
        return render_template('ai_dashboard.html', title='Dashboard de IA', data=dashboard_data)
    
    @app.route('/ai/patterns')
    @login_required
    def ai_patterns():
        """Página de padrões identificados"""
        patterns = db.session.query(OccurrencePattern).all()
        return render_template('ai_patterns.html', title='Padrões Identificados', patterns=patterns)
    
    @app.route('/ai/predictions')
    @login_required
    def ai_predictions():
        """Página de previsões geradas"""
        predictions = db.session.query(OccurrencePrediction).all()
        return render_template('ai_predictions.html', title='Previsões', predictions=predictions)
    
    @app.route('/ai/alerts')
    @login_required
    def ai_alerts():
        """Página de alertas preventivos"""
        alerts = db.session.query(PreventiveAlert).all()
        return render_template('ai_alerts.html', title='Alertas Preventivos', alerts=alerts)
    
    @app.route('/ai/automated-warnings')
    @login_required
    def ai_automated_warnings():
        """Página de advertências automatizadas"""
        warnings = db.session.query(AutomatedWarning).all()
        return render_template('ai_automated_warnings.html', title='Advertências Automatizadas', warnings=warnings)
    
    @app.route('/ai/rules')
    @login_required
    def ai_rules():
        """Página de regras de automação"""
        rules = db.session.query(AutomatedWarningRule).all()
        return render_template('ai_rules.html', title='Regras de Automação', rules=rules)
    
    @app.route('/ai/analyze', methods=['POST'])
    @login_required
    def ai_analyze():
        """Rota para analisar padrões"""
        patterns = ai_manager.analyze_patterns()
        
        return jsonify({
            'success': True,
            'message': f'Análise concluída. {len(patterns)} padrões identificados.',
            'patterns': [{'id': p.id, 'description': p.description} for p in patterns]
        })
    
    @app.route('/ai/predict', methods=['POST'])
    @login_required
    def ai_predict():
        """Rota para gerar previsões"""
        predictions = ai_manager.generate_predictions()
        
        return jsonify({
            'success': True,
            'message': f'Previsão concluída. {len(predictions)} previsões geradas.',
            'predictions': [{'id': p.id, 'type': p.prediction_type, 'probability': p.probability} for p in predictions]
        })
    
    @app.route('/ai/generate-measures', methods=['POST'])
    @login_required
    def ai_generate_measures():
        """Rota para gerar medidas preventivas"""
        prediction_id = request.form.get('prediction_id')
        if prediction_id:
            prediction_id = int(prediction_id)
        
        mappings = ai_manager.generate_preventive_measures(prediction_id)
        
        return jsonify({
            'success': True,
            'message': f'{len(mappings)} medidas preventivas geradas.',
            'count': len(mappings)
        })
    
    @app.route('/ai/generate-alerts', methods=['POST'])
    @login_required
    def ai_generate_alerts():
        """Rota para gerar alertas preventivos"""
        prediction_id = request.form.get('prediction_id')
        if prediction_id:
            prediction_id = int(prediction_id)
        
        min_probability = request.form.get('min_probability', 0.6)
        if isinstance(min_probability, str):
            min_probability = float(min_probability)
        
        alerts = ai_manager.generate_preventive_alerts(prediction_id, min_probability)
        
        return jsonify({
            'success': True,
            'message': f'{len(alerts)} alertas preventivos gerados.',
            'alerts': [{'id': a.id, 'title': a.title, 'level': a.alert_level} for a in alerts]
        })
    
    @app.route('/ai/process-rules', methods=['POST'])
    @login_required
    def ai_process_rules():
        """Rota para processar regras de advertências automatizadas"""
        warnings = ai_manager.process_automated_warning_rules()
        
        return jsonify({
            'success': True,
            'message': f'{len(warnings)} advertências automatizadas geradas.',
            'warnings': [{'id': w.id, 'status': w.status} for w in warnings]
        })
    
    @app.route('/ai/approve-warning/<int:warning_id>', methods=['POST'])
    @login_required
    def ai_approve_warning(warning_id):
        """Rota para aprovar uma advertência automatizada"""
        success = ai_manager.approve_automated_warning(warning_id, current_user.id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Advertência aprovada com sucesso.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Erro ao aprovar advertência. Verifique se ela existe e está pendente.'
            }), 400
    
    @app.route('/ai/send-warning/<int:warning_id>', methods=['POST'])
    @login_required
    def ai_send_warning(warning_id):
        """Rota para enviar uma advertência automatizada"""
        success = ai_manager.send_automated_warning(warning_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Advertência enviada com sucesso.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Erro ao enviar advertência. Verifique se ela existe e está aprovada.'
            }), 400
    
    @app.route('/ai/cancel-warning/<int:warning_id>', methods=['POST'])
    @login_required
    def ai_cancel_warning(warning_id):
        """Rota para cancelar uma advertência automatizada"""
        reason = request.form.get('reason')
        success = ai_manager.cancel_automated_warning(warning_id, reason)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Advertência cancelada com sucesso.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Erro ao cancelar advertência. Verifique se ela existe e está pendente ou aprovada.'
            }), 400
    
    @app.route('/ai/rule/new', methods=['GET', 'POST'])
    @login_required
    def ai_new_rule():
        """Página para criar nova regra de automação"""
        if request.method == 'POST':
            name = request.form.get('name')
            description = request.form.get('description')
            trigger_type = request.form.get('trigger_type')
            trigger_condition = request.form.get('trigger_condition')
            trigger_value = request.form.get('trigger_value')
            warning_template_id = request.form.get('warning_template_id')
            auto_send = request.form.get('auto_send') == 'true'
            
            rule = AutomatedWarningRule(
                name=name,
                description=description,
                trigger_type=trigger_type,
                trigger_condition=trigger_condition,
                trigger_value=trigger_value,
                warning_template_id=warning_template_id,
                auto_send=auto_send,
                created_by=current_user.id
            )
            
            db.session.add(rule)
            db.session.commit()
            
            flash('Regra criada com sucesso!', 'success')
            return redirect(url_for('ai_rules'))
        
        return render_template('ai_rule_form.html', title='Nova Regra de Automação')
    
    @app.route('/ai/rule/edit/<int:rule_id>', methods=['GET', 'POST'])
    @login_required
    def ai_edit_rule(rule_id):
        """Página para editar regra de automação"""
        rule = db.session.query(AutomatedWarningRule).filter_by(id=rule_id).first()
        
        if not rule:
            flash('Regra não encontrada', 'danger')
            return redirect(url_for('ai_rules'))
        
        if request.method == 'POST':
            rule.name = request.form.get('name')
            rule.description = request.form.get('description')
            rule.trigger_type = request.form.get('trigger_type')
            rule.trigger_condition = request.form.get('trigger_condition')
            rule.trigger_value = request.form.get('trigger_value')
            rule.warning_template_id = request.form.get('warning_template_id')
            rule.auto_send = request.form.get('auto_send') == 'true'
            rule.is_active = request.form.get('is_active') == 'true'
            
            db.session.commit()
            
            flash('Regra atualizada com sucesso!', 'success')
            return redirect(url_for('ai_rules'))
        
        return render_template('ai_rule_form.html', title='Editar Regra de Automação', rule=rule)
    
    @app.route('/api/ai/dashboard-data')
    @login_required
    def api_ai_dashboard_data():
        """API para obter dados do dashboard de IA"""
        dashboard_data = ai_manager.get_dashboard_data()
        return jsonify(dashboard_data)
