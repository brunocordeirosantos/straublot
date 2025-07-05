
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
import os
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import hashlib

# Importar pytz com tratamento de erro
try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False
    st.warning("⚠️ Biblioteca pytz não encontrada. Usando horário UTC.")

# Função para obter hora de Brasília com fallback
def obter_horario_brasilia():
    if PYTZ_AVAILABLE:
        try:
            tz_brasilia = pytz.timezone("America/Sao_Paulo")
            agora = datetime.now(tz_brasilia)
            return agora.strftime("%H:%M:%S")
        except:
            pass
    return datetime.now().strftime("%H:%M:%S")

# Função segura para converter em Decimal
def safe_decimal(valor):
    try:
        return Decimal(str(valor).replace(",", "."))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")

# Exemplo de DataFrame de operações
df_operacoes = pd.DataFrame({
    "Valor_Bruto": ["1515", "2024,77", "NaN"],
    "Taxa_Cliente": ["15,15", "40,5", ""],
    "Taxa_Banco": ["0.01", "0", "nan"]
})

# Conversão de colunas para Decimal
for col in ["Valor_Bruto", "Taxa_Cliente", "Taxa_Banco"]:
    df_operacoes[col] = df_operacoes[col].apply(safe_decimal)

# Cálculos com Decimal
df_operacoes["Valor_Liquido"] = df_operacoes["Valor_Bruto"] - df_operacoes["Taxa_Cliente"] - df_operacoes["Taxa_Banco"]
df_operacoes["Lucro"] = df_operacoes["Valor_Bruto"] - df_operacoes["Valor_Liquido"]

# Arredondamento
df_operacoes["Valor_Liquido"] = df_operacoes["Valor_Liquido"].apply(lambda x: x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
df_operacoes["Lucro"] = df_operacoes["Lucro"].apply(lambda x: x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

# Exibição no Streamlit
st.write(df_operacoes)
