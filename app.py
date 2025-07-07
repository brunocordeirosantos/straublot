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

# ===== FUNÇÕES AUXILIARES PARA CONVERSÃO E FORMATAÇÃO =====

def to_decimal(value):
    """Converte qualquer valor para Decimal de forma segura"""
    try:
        if isinstance(value, Decimal):
            return value
        if isinstance(value, str):
            # Remove espaços e converte vírgulas para pontos se necessário
            value = value.strip().replace(',', '.')
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0')

def to_float(value):
    """Converte Decimal ou string para float de forma segura"""
    try:
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, str):
            value = value.strip().replace(',', '.')
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def format_currency(value):
    """Formata valor como moeda brasileira"""
    try:
        val = to_float(value)
        return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return "R$ 0,00"

def format_currency_us(value):
    """Formata valor no padrão americano para Google Sheets"""
    try:
        val = to_float(value)
        return f"{val:.2f}"
    except:
        return "0.00"

def format_percentage(value, total):
    """Formata porcentagem de forma segura"""
    try:
        val = to_float(value)
        tot = to_float(total)
        if tot == 0:
            return "0.00%"
        return f"{(val / tot) * 100:.2f}%"
    except:
        return "0.00%"

# Funções para horário de Brasília com fallback
def obter_horario_brasilia():
    """Retorna hora atual no fuso horário de Brasília"""
    if PYTZ_AVAILABLE:
        try:
            tz_brasilia = pytz.timezone("America/Sao_Paulo")
            agora = datetime.now(tz_brasilia)
            return agora.strftime("%H:%M:%S")
        except:
            pass
    return datetime.now().strftime("%H:%M:%S")

def obter_data_brasilia():
    """Retorna data atual no fuso horário de Brasília"""
    if PYTZ_AVAILABLE:
        try:
            tz_brasilia = pytz.timezone("America/Sao_Paulo")
            agora = datetime.now(tz_brasilia)
            return agora.strftime("%Y-%m-%d")
        except:
            pass
    return datetime.now().strftime("%Y-%m-%d")

def obter_datetime_brasilia():
    """Retorna datetime atual no fuso horário de Brasília"""
    if PYTZ_AVAILABLE:
        try:
            tz_brasilia = pytz.timezone("America/Sao_Paulo")
            return datetime.now(tz_brasilia)
        except:
            pass
    return datetime.now()

def obter_date_brasilia():
    """Retorna date atual no fuso horário de Brasília"""
    if PYTZ_AVAILABLE:
        try:
            tz_brasilia = pytz.timezone("America/Sao_Paulo")
            agora = datetime.now(tz_brasilia)
            return agora.date()
        except:
            pass
    return date.today()

# Configuração da página
st.set_page_config(
    page_title="Sistema Unificado - Lotérica & Caixa Interno",
    page_icon="🏧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado para interface moderna
st.markdown("""
<style>
    @import url("https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap");
    
    html, body, [class*="css"] {
        font-family: "Inter", sans-serif;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .metric-card h3 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
        color: white;
    }
    
    .metric-card p {
        margin: 0.5rem 0 0 0;
        font-size: 0.9rem;
        color: rgba(255, 255, 255, 0.9);
        font-weight: 500;
    }
    
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    .stSelectbox > div > div {
        border-radius: 8px;
    }
    
    .stNumberInput > div > div {
        border-radius: 8px;
    }
    
    .stTextInput > div > div {
        border-radius: 8px;
    }
    
    .stTextArea > div > div {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ===== FUNÇÕES DE CONEXÃO E DADOS =====

@st.cache_resource
def conectar_google_sheets():
    """Conecta ao Google Sheets usando Streamlit Secrets"""
    try:
        # Tentar usar Streamlit Secrets primeiro (para deploy)
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            credentials_dict = dict(st.secrets["gcp_service_account"])
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
            gc = gspread.authorize(credentials)
            spreadsheet = gc.open("Lotericabasededados")
            st.success("🔗 Conectado via Streamlit Secrets (Deploy)")
            return spreadsheet
        else:
            st.warning("⚠️ Streamlit Secrets não disponível")
            return None
    except Exception as e:
        st.error(f"❌ Erro na conexão: {str(e)}")
        return None

@st.cache_data(ttl=60)
def buscar_dados(_spreadsheet, sheet_name):
    """Busca dados do Google Sheets com cache"""
    try:
        if _spreadsheet is None:
            return []
        worksheet = _spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return data
    except Exception as e:
        st.warning(f"⚠️ Erro ao buscar dados de {sheet_name}: {str(e)}")
        return []

def normalizar_dados_inteligente(dados):
    """Normaliza dados vindos do Google Sheets"""
    if not dados:
        return []
    
    dados_normalizados = []
    for item in dados:
        item_normalizado = {}
        for chave, valor in item.items():
            if isinstance(valor, str):
                # Tentar converter valores numéricos
                try:
                    if '.' in valor and valor.replace('.', '').replace('-', '').isdigit():
                        item_normalizado[chave] = to_float(valor)
                    else:
                        item_normalizado[chave] = valor
                except:
                    item_normalizado[chave] = valor
            else:
                item_normalizado[chave] = valor
        dados_normalizados.append(item_normalizado)
    
    return dados_normalizados

def salvar_operacao_segura(worksheet, dados):
    """Salva operação convertendo Decimal para float"""
    try:
        dados_convertidos = []
        for item in dados:
            if isinstance(item, Decimal):
                dados_convertidos.append(to_float(item))
            else:
                dados_convertidos.append(item)
        
        worksheet.append_row(dados_convertidos)
        return True
    except Exception as e:
        st.error(f"❌ Erro ao salvar: {str(e)}")
        return False

def get_or_create_worksheet(spreadsheet, sheet_name, headers):
    """Cria ou obtém worksheet"""
    try:
        if spreadsheet is None:
            return None
        
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="20")
            worksheet.append_row(headers)
        
        return worksheet
    except Exception as e:
        st.error(f"❌ Erro ao acessar planilha {sheet_name}: {str(e)}")
        return None

# ===== FUNÇÕES DE CÁLCULO =====

def calcular_taxa_cartao_debito(valor):
    """Calcula taxa para cartão débito"""
    valor_dec = to_decimal(valor)
    taxa_cliente = (valor_dec * Decimal('0.01')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    taxa_banco = Decimal('1.00')
    lucro = taxa_cliente - taxa_banco
    valor_liquido = valor_dec - taxa_cliente
    
    return {
        "taxa_cliente": taxa_cliente,
        "taxa_banco": taxa_banco,
        "valor_liquido": valor_liquido,
        "lucro": lucro
    }

def calcular_taxa_cartao_credito(valor):
    """Calcula taxa para cartão crédito"""
    valor_dec = to_decimal(valor)
    taxa_cliente = (valor_dec * Decimal('0.0533')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    taxa_banco = (valor_dec * Decimal('0.0433')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    lucro = taxa_cliente - taxa_banco
    valor_liquido = valor_dec - taxa_cliente
    
    return {
        "taxa_cliente": taxa_cliente,
        "taxa_banco": taxa_banco,
        "valor_liquido": valor_liquido,
        "lucro": lucro
    }

def calcular_taxa_cheque_vista(valor):
    """Calcula taxa para cheque à vista"""
    valor_dec = to_decimal(valor)
    taxa_cliente = (valor_dec * Decimal('0.02')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    taxa_banco = Decimal('0.00')
    lucro = taxa_cliente
    valor_liquido = valor_dec - taxa_cliente
    
    return {
        "taxa_cliente": taxa_cliente,
        "taxa_banco": taxa_banco,
        "valor_liquido": valor_liquido,
        "lucro": lucro
    }

def calcular_taxa_cheque_predatado(valor, dias):
    """Calcula taxa para cheque pré-datado"""
    valor_dec = to_decimal(valor)
    dias_dec = to_decimal(dias)
    
    taxa_base = valor_dec * Decimal('0.02')
    taxa_dias = valor_dec * Decimal('0.0033') * dias_dec
    taxa_cliente = (taxa_base + taxa_dias).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    taxa_banco = Decimal('0.00')
    lucro = taxa_cliente
    valor_liquido = valor_dec - taxa_cliente
    
    return {
        "taxa_cliente": taxa_cliente,
        "taxa_banco": taxa_banco,
        "valor_liquido": valor_liquido,
        "lucro": lucro
    }

def calcular_taxa_cheque_manual(valor, taxa_percentual):
    """Calcula taxa manual para cheque"""
    valor_dec = to_decimal(valor)
    taxa_dec = to_decimal(taxa_percentual) / Decimal('100')
    
    taxa_cliente = (valor_dec * taxa_dec).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    taxa_banco = Decimal('0.00')
    lucro = taxa_cliente
    valor_liquido = valor_dec - taxa_cliente
    
    return {
        "taxa_cliente": taxa_cliente,
        "taxa_banco": taxa_banco,
        "valor_liquido": valor_liquido,
        "lucro": lucro
    }

# ===== SISTEMA DE AUTENTICAÇÃO =====

def hash_password(password):
    """Gera hash da senha"""
    return hashlib.sha256(password.encode()).hexdigest()

def verificar_login(usuario, senha):
    """Verifica credenciais de login"""
    usuarios = {
        "gerente": {"senha": hash_password("gerente123"), "perfil": "Gerente"},
        "caixa": {"senha": hash_password("caixa123"), "perfil": "Operador Caixa"},
        "loterica": {"senha": hash_password("loterica123"), "perfil": "Operador Lotérica"}
    }
    
    if usuario in usuarios and usuarios[usuario]["senha"] == hash_password(senha):
        return usuarios[usuario]["perfil"]
    return None

def render_login():
    """Renderiza tela de login"""
    st.markdown("""
    <div style="text-align: center; padding: 2rem;">
        <h1>🏧 Sistema Unificado</h1>
        <h3>Lotérica & Caixa Interno</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            st.markdown("### 🔐 Acesso ao Sistema")
            usuario = st.text_input("👤 Usuário")
            senha = st.text_input("🔑 Senha", type="password")
            
            if st.form_submit_button("🚀 Entrar", use_container_width=True):
                perfil = verificar_login(usuario, senha)
                if perfil:
                    st.session_state.logado = True
                    st.session_state.usuario = usuario
                    st.session_state.perfil = perfil
                    st.session_state.nome_usuario = perfil
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos!")

# ===== DASHBOARD PRINCIPAL =====

def render_dashboard_caixa(spreadsheet):
    """Renderiza dashboard do caixa interno"""
    st.subheader("💳 Dashboard Caixa Interno")
    
    try:
        HEADERS = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]
        operacoes_data = buscar_dados(spreadsheet, "Operacoes_Caixa")
        
        if not operacoes_data:
            st.info("📊 Nenhuma operação registrada para exibir o dashboard.")
            return
        
        # Normalizar dados
        operacoes_data_normalizada = normalizar_dados_inteligente(operacoes_data)
        df_operacoes = pd.DataFrame(operacoes_data_normalizada)
        
        # Converter colunas numéricas
        for col in ["Valor_Bruto", "Valor_Liquido", "Taxa_Cliente", "Taxa_Banco", "Lucro"]:
            if col in df_operacoes.columns:
                df_operacoes[col] = pd.to_numeric(df_operacoes[col], errors="coerce").fillna(0)
        
        # Calcular métricas
        total_suprimentos = df_operacoes[df_operacoes["Tipo_Operacao"] == "Suprimento"]["Valor_Bruto"].sum()
        tipos_de_saida = ["Saque Cartão Débito", "Saque Cartão Crédito", "Cheque à Vista", "Cheque Pré-datado", "Cheque com Taxa Manual"]
        total_saques_liquidos = df_operacoes[df_operacoes["Tipo_Operacao"].isin(tipos_de_saida)]["Valor_Liquido"].sum()
        
        # Separar por tipo
        tipos_cartao = ["Saque Cartão Débito", "Saque Cartão Crédito"]
        tipos_cheque = ["Cheque à Vista", "Cheque Pré-datado", "Cheque com Taxa Manual"]
        total_cartoes = df_operacoes[df_operacoes["Tipo_Operacao"].isin(tipos_cartao)]["Valor_Liquido"].sum()
        total_cheques = df_operacoes[df_operacoes["Tipo_Operacao"].isin(tipos_cheque)]["Valor_Liquido"].sum()
        
        # Saldo do caixa
        saldo_inicial = 0
        saldo_caixa = saldo_inicial + total_suprimentos - total_saques_liquidos
        
        # Operações de hoje
        hoje_str = obter_data_brasilia()
        operacoes_de_hoje = df_operacoes[df_operacoes["Data"] == hoje_str]
        operacoes_hoje_count = len(operacoes_de_hoje)
        valor_saque_hoje = operacoes_de_hoje[operacoes_de_hoje["Tipo_Operacao"].isin(tipos_de_saida)]["Valor_Liquido"].sum()
        
        # Exibir métricas em cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">
                <h3>{format_currency(saldo_caixa)}</h3>
                <p>💰 Saldo do Caixa</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                <h3>{format_currency(total_cartoes)}</h3>
                <p>💳 Total Cartões</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                <h3>{format_currency(total_cheques)}</h3>
                <p>📄 Total Cheques</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            total_geral = total_cartoes + total_cheques
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);">
                <h3>{format_currency(total_geral)}</h3>
                <p>📊 Total Geral</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Segunda linha de métricas
        st.markdown("<br>", unsafe_allow_html=True)
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);">
                <h3>{format_currency(valor_saque_hoje)}</h3>
                <p>📅 Saques Hoje</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col6:
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #d299c2 0%, #fef9d7 100%);">
                <h3>{operacoes_hoje_count}</h3>
                <p>📋 Operações Hoje</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col7:
            status_cor = "#38ef7d" if saldo_caixa > 2000 else "#f5576c"
            status_texto = "Normal" if saldo_caixa > 2000 else "Baixo"
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, {status_cor} 0%, {status_cor} 100%);">
                <h3>{status_texto}</h3>
                <p>🚦 Status Caixa</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col8:
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #89f7fe 0%, #66a6ff 100%);">
                <h3>{format_currency(total_suprimentos)}</h3>
                <p>💰 Suprimentos</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Gráfico de resumo
        if len(df_operacoes) > 0:
            st.markdown("### 📊 Resumo de Operações (Últimos 7 Dias)")
            
            try:
                df_operacoes["Data"] = pd.to_datetime(df_operacoes["Data"], errors='coerce')
                data_limite = pd.Timestamp.now() - pd.Timedelta(days=7)
                df_recente = df_operacoes[df_operacoes["Data"] >= data_limite]
                
                if not df_recente.empty:
                    resumo_por_tipo = df_recente.groupby("Tipo_Operacao")["Valor_Liquido"].sum().reset_index()
                    
                    fig = px.bar(
                        resumo_por_tipo,
                        x="Tipo_Operacao",
                        y="Valor_Liquido",
                        title="Valores por Tipo de Operação",
                        color="Valor_Liquido",
                        color_continuous_scale="viridis"
                    )
                    
                    fig.update_layout(
                        xaxis_title="Tipo de Operação",
                        yaxis_title="Valor Líquido (R$)",
                        showlegend=False,
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("📊 Nenhuma operação nos últimos 7 dias.")
            
            except Exception as e:
                st.warning(f"⚠️ Erro ao gerar gráfico: {str(e)}")
        
        # Alertas de saldo baixo
        if saldo_caixa < 1000:
            st.error("🚨 **ATENÇÃO:** Saldo do caixa está muito baixo! Considere fazer um suprimento.")
        elif saldo_caixa < 2000:
            st.warning("⚠️ **AVISO:** Saldo do caixa está baixo. Monitore para possível suprimento.")
    
    except Exception as e:
        st.error(f"❌ Erro ao carregar dashboard: {str(e)}")

# ===== GESTÃO DO COFRE =====

def render_cofre(spreadsheet):
    """Renderiza gestão do cofre"""
    st.subheader("🏦 Gestão do Cofre")
    
    # Headers para cofre
    HEADERS_COFRE = ["Data", "Hora", "Operador", "Tipo_Movimentacao", "Valor", "Origem_Destino", "Observacoes"]
    
    tab1, tab2 = st.tabs(["📝 Registrar Movimentação", "📊 Histórico do Cofre"])
    
    with tab1:
        st.markdown("### 🆕 Nova Movimentação no Cofre")
        
        with st.form("form_cofre", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                tipo_movimentacao = st.selectbox("Tipo de Movimentação", ["Entrada no Cofre", "Saída do Cofre"])
                valor_movimentacao = st.number_input("Valor da Movimentação (R$)", min_value=0.01, step=100.0, format="%.2f")
            
            with col2:
                if tipo_movimentacao == "Entrada no Cofre":
                    origem_destino = st.text_input("Origem da Entrada (Ex: Banco, Sócio)")
                else:
                    origem_destino = st.selectbox("Destino da Saída", ["Caixa Interno", "Banco", "Despesas", "Outro"])
                
                observacoes = st.text_area("Observações Adicionais")
            
            if st.form_submit_button("💾 Salvar Movimentação", use_container_width=True):
                try:
                    worksheet = get_or_create_worksheet(spreadsheet, "Operacoes_Cofre", HEADERS_COFRE)
                    
                    if worksheet:
                        nova_movimentacao = [
                            obter_data_brasilia(),
                            obter_horario_brasilia(),
                            st.session_state.nome_usuario,
                            tipo_movimentacao,
                            format_currency_us(valor_movimentacao),
                            origem_destino,
                            observacoes
                        ]
                        
                        if salvar_operacao_segura(worksheet, nova_movimentacao):
                            st.success(f"✅ Movimentação de {format_currency(valor_movimentacao)} no cofre registrada com sucesso!")
                            st.cache_data.clear()
                        
                except Exception as e:
                    st.error(f"❌ Erro ao salvar movimentação: {str(e)}")
    
    with tab2:
        st.markdown("### 📊 Histórico de Movimentações do Cofre")
        
        try:
            cofre_data = buscar_dados(spreadsheet, "Operacoes_Cofre")
            
            if cofre_data:
                df_cofre = pd.DataFrame(cofre_data)
                
                # Converter valores para exibição
                if "Valor" in df_cofre.columns:
                    df_cofre["Valor_Display"] = df_cofre["Valor"].apply(lambda x: format_currency(x))
                
                # Ordenar por data e hora
                try:
                    if "Data" in df_cofre.columns and "Hora" in df_cofre.columns:
                        df_cofre_sorted = df_cofre.sort_values(by=["Data", "Hora"], ascending=False)
                        st.dataframe(df_cofre_sorted, use_container_width=True)
                    else:
                        st.dataframe(df_cofre, use_container_width=True)
                except Exception as e:
                    st.warning("⚠️ Erro ao ordenar dados. Exibindo sem ordenação.")
                    st.dataframe(df_cofre, use_container_width=True)
            else:
                st.info("Nenhuma movimentação registrada no cofre.")
        
        except Exception as e:
            st.error(f"❌ Erro ao carregar gestão do cofre: {str(e)}")

# ===== OPERAÇÕES DO CAIXA =====

def render_operacoes_caixa(spreadsheet):
    """Renderiza operações do caixa interno"""
    st.subheader("💳 Operações do Caixa Interno")
    
    HEADERS = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]
    
    tab1, tab2, tab3, tab4 = st.tabs(["💳 Saque Cartão", "📄 Troca de Cheques", "🔄 Suprimento Caixa", "📊 Histórico"])
    
    with tab1:
        st.markdown("### 💳 Saque com Cartão")
        
        with st.form("form_saque_cartao", clear_on_submit=False):
            # Campo de operador
            operador_selecionado = st.selectbox("👤 Operador Responsável", 
                ["Bruna", "Karina", "Edson", "Robson", "Adiel", "Lucas", "Ana Paula", "Fernanda"], key="op_cartao")
            
            col1, col2 = st.columns(2)
            
            with col1:
                tipo_cartao = st.selectbox("Tipo de Cartão", ["Débito", "Crédito"])
                valor = st.number_input("Valor do Saque (R$)", min_value=0.01, step=100.0, key="valor_cartao", format="%.2f")
                nome = st.text_input("Nome do Cliente (Opcional)", key="nome_cartao")
            
            with col2:
                cpf = st.text_input("CPF do Cliente (Opcional)", key="cpf_cartao")
                observacoes = st.text_area("Observações", key="obs_cartao")
            
            col_sim, col_conf = st.columns(2)
            
            with col_sim:
                simular = st.form_submit_button("🧮 Simular Operação", use_container_width=True)
            
            with col_conf:
                confirmar = st.form_submit_button("💾 Confirmar e Salvar", use_container_width=True)
            
            if simular and valor > 0:
                if tipo_cartao == "Débito":
                    calc = calcular_taxa_cartao_debito(valor)
                    tipo_operacao = "Saque Cartão Débito"
                else:
                    calc = calcular_taxa_cartao_credito(valor)
                    tipo_operacao = "Saque Cartão Crédito"
                
                st.markdown("---")
                st.markdown("### 🧮 Simulação - Cartão")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Taxa Percentual", format_percentage(calc['taxa_cliente'], valor))
                with col2:
                    st.metric("Taxa em Valores", format_currency(calc['taxa_cliente']))
                with col3:
                    st.metric("💵 Valor a Entregar", format_currency(calc['valor_liquido']))
                
                st.session_state.simulacao_atual = {
                    "tipo": tipo_operacao,
                    "dados": calc,
                    "valor_bruto": valor,
                    "nome": nome or "Não informado",
                    "cpf": cpf or "Não informado",
                    "observacoes": observacoes,
                    "data_vencimento": ""
                }
            
            if confirmar and hasattr(st.session_state, 'simulacao_atual'):
                try:
                    sim_data = st.session_state.simulacao_atual
                    worksheet = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", HEADERS)
                    
                    if worksheet:
                        nova_operacao = [
                            obter_data_brasilia(),
                            obter_horario_brasilia(),
                            operador_selecionado,
                            sim_data["tipo"],
                            sim_data["nome"],
                            sim_data["cpf"],
                            format_currency_us(sim_data["valor_bruto"]),
                            format_currency_us(sim_data["dados"]["taxa_cliente"]),
                            format_currency_us(sim_data["dados"]["taxa_banco"]),
                            format_currency_us(sim_data["dados"]["valor_liquido"]),
                            format_currency_us(sim_data["dados"]["lucro"]),
                            "Concluído",
                            sim_data["data_vencimento"],
                            format_percentage(sim_data["dados"]["taxa_cliente"], sim_data["valor_bruto"]),
                            sim_data["observacoes"]
                        ]
                        
                        if salvar_operacao_segura(worksheet, nova_operacao):
                            st.success(f"✅ {sim_data['tipo']} de {format_currency(sim_data['valor_bruto'])} registrado com sucesso!")
                            del st.session_state.simulacao_atual
                            st.cache_data.clear()
                
                except Exception as e:
                    st.error(f"❌ Erro ao salvar operação: {str(e)}")
    
    with tab2:
        st.markdown("### 📄 Troca de Cheques")
        
        with st.form("form_troca_cheque", clear_on_submit=False):
            # Campo de operador
            operador_selecionado_cheque = st.selectbox("👤 Operador Responsável", 
                ["Bruna", "Karina", "Edson", "Robson", "Adiel", "Lucas", "Ana Paula", "Fernanda"], key="op_cheque")
            
            col1, col2 = st.columns(2)
            
            with col1:
                tipo_cheque = st.selectbox("Tipo de Cheque", ["Cheque à Vista", "Cheque Pré-datado", "Cheque com Taxa Manual"])
                valor = st.number_input("Valor do Cheque (R$)", min_value=0.01, step=100.0, key="valor_cheque", format="%.2f")
                nome = st.text_input("Nome do Cliente (Opcional)", key="nome_cheque")
            
            with col2:
                cpf = st.text_input("CPF do Cliente (Opcional)", key="cpf_cheque")
                observacoes = st.text_area("Observações", key="obs_cheque")
            
            # Campos específicos por tipo de cheque
            dias = 0
            taxa_manual = 0
            data_vencimento = ""
            
            if tipo_cheque == "Cheque Pré-datado":
                dias = st.number_input("Dias até o vencimento", min_value=1, max_value=365, value=30)
                data_vencimento = (obter_date_brasilia() + timedelta(days=dias)).strftime("%Y-%m-%d")
                st.info(f"📅 Data de vencimento: {data_vencimento}")
            elif tipo_cheque == "Cheque com Taxa Manual":
                taxa_manual = st.number_input("Taxa Manual (%)", min_value=0.1, max_value=50.0, value=2.0, step=0.1, format="%.1f")
            
            col_sim, col_conf = st.columns(2)
            
            with col_sim:
                simular = st.form_submit_button("🧮 Simular Operação", use_container_width=True)
            
            with col_conf:
                confirmar = st.form_submit_button("💾 Confirmar e Salvar", use_container_width=True)
            
            if simular and valor > 0:
                if tipo_cheque == "Cheque à Vista":
                    calc = calcular_taxa_cheque_vista(valor)
                elif tipo_cheque == "Cheque Pré-datado":
                    calc = calcular_taxa_cheque_predatado(valor, dias)
                else:
                    calc = calcular_taxa_cheque_manual(valor, taxa_manual)
                
                st.markdown("---")
                st.markdown("### 🧮 Simulação - Cheque")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Taxa Percentual", format_percentage(calc['taxa_cliente'], valor))
                with col2:
                    st.metric("Taxa em Valores", format_currency(calc['taxa_cliente']))
                with col3:
                    st.metric("💵 Valor a Entregar", format_currency(calc['valor_liquido']))
                
                if tipo_cheque == "Cheque à Vista":
                    st.info("💡 Taxa de 2% sobre o valor do cheque")
                elif tipo_cheque == "Cheque Pré-datado":
                    st.info(f"💡 Taxa de 2% + 0,33% por dia ({dias} dias)")
                else:
                    st.info(f"💡 Taxa manual de {taxa_manual}%")
                
                st.session_state.simulacao_atual = {
                    "tipo": tipo_cheque,
                    "dados": calc,
                    "valor_bruto": valor,
                    "nome": nome or "Não informado",
                    "cpf": cpf or "Não informado",
                    "observacoes": observacoes,
                    "data_vencimento": data_vencimento
                }
            
            if confirmar and hasattr(st.session_state, 'simulacao_atual'):
                try:
                    sim_data = st.session_state.simulacao_atual
                    worksheet = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", HEADERS)
                    
                    if worksheet:
                        nova_operacao = [
                            obter_data_brasilia(),
                            obter_horario_brasilia(),
                            operador_selecionado_cheque,
                            sim_data["tipo"],
                            sim_data["nome"],
                            sim_data["cpf"],
                            format_currency_us(sim_data["valor_bruto"]),
                            format_currency_us(sim_data["dados"]["taxa_cliente"]),
                            format_currency_us(sim_data["dados"]["taxa_banco"]),
                            format_currency_us(sim_data["dados"]["valor_liquido"]),
                            format_currency_us(sim_data["dados"]["lucro"]),
                            "Concluído",
                            sim_data["data_vencimento"],
                            format_percentage(sim_data["dados"]["taxa_cliente"], sim_data["valor_bruto"]),
                            sim_data["observacoes"]
                        ]
                        
                        if salvar_operacao_segura(worksheet, nova_operacao):
                            st.success(f"✅ {sim_data['tipo']} de {format_currency(sim_data['valor_bruto'])} registrado com sucesso!")
                            del st.session_state.simulacao_atual
                            st.cache_data.clear()
                
                except Exception as e:
                    st.error(f"❌ Erro ao salvar operação: {str(e)}")
    
    with tab3:
        st.markdown("### 🔄 Suprimento do Caixa")
        
        with st.form("form_suprimento", clear_on_submit=True):
            # Campo de operador
            operador_selecionado_suprimento = st.selectbox("👤 Operador Responsável", 
                ["Bruna", "Karina", "Edson", "Robson", "Adiel", "Lucas", "Ana Paula", "Fernanda"], key="op_suprimento")
            
            valor_suprimento = st.number_input("Valor do Suprimento (R$)", min_value=0.01, step=100.0, format="%.2f")
            origem_suprimento = st.selectbox("Origem do Suprimento", ["Cofre Principal", "Banco", "Outro"])
            observacoes_sup = st.text_area("Observações do Suprimento")
            
            if st.form_submit_button("💰 Registrar Suprimento", use_container_width=True):
                try:
                    worksheet = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", HEADERS)
                    
                    if worksheet:
                        nova_operacao = [
                            obter_data_brasilia(),
                            obter_horario_brasilia(),
                            operador_selecionado_suprimento,
                            "Suprimento",
                            "Sistema",
                            "N/A",
                            format_currency_us(valor_suprimento),
                            "0.00",
                            "0.00",
                            format_currency_us(valor_suprimento),
                            "0.00",
                            "Concluído",
                            "",
                            "0.00%",
                            f"Origem: {origem_suprimento}. {observacoes_sup}"
                        ]
                        
                        if salvar_operacao_segura(worksheet, nova_operacao):
                            st.success(f"✅ Suprimento de {format_currency(valor_suprimento)} registrado com sucesso!")
                            st.cache_data.clear()
                
                except Exception as e:
                    st.error(f"❌ Erro ao salvar suprimento: {str(e)}")
    
    with tab4:
        st.markdown("### 📊 Histórico de Operações")
        
        try:
            operacoes_data = buscar_dados(spreadsheet, "Operacoes_Caixa")
            
            if operacoes_data:
                operacoes_data_normalizada = normalizar_dados_inteligente(operacoes_data)
                df_operacoes = pd.DataFrame(operacoes_data_normalizada)
                
                # Filtros
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    data_inicio = st.date_input("Data Início", value=obter_date_brasilia() - timedelta(days=30))
                
                with col2:
                    data_fim = st.date_input("Data Fim", value=obter_date_brasilia())
                
                with col3:
                    tipo_operacao_filtro = st.selectbox("Tipo de Operação", 
                        ["Todos", "Saque Cartão Débito", "Saque Cartão Crédito", "Cheque à Vista", "Cheque Pré-datado", "Suprimento"])
                
                # Aplicar filtros
                df_filtrado = df_operacoes.copy()
                
                if "Data" in df_filtrado.columns:
                    df_filtrado["Data"] = pd.to_datetime(df_filtrado["Data"], errors='coerce')
                    df_filtrado = df_filtrado[
                        (df_filtrado["Data"] >= pd.Timestamp(data_inicio)) &
                        (df_filtrado["Data"] <= pd.Timestamp(data_fim))
                    ]
                
                if tipo_operacao_filtro != "Todos":
                    df_filtrado = df_filtrado[df_filtrado["Tipo_Operacao"] == tipo_operacao_filtro]
                
                if not df_filtrado.empty:
                    # Ordenar por data e hora
                    try:
                        if "Data" in df_filtrado.columns and "Hora" in df_filtrado.columns:
                            df_filtrado = df_filtrado.sort_values(by=["Data", "Hora"], ascending=False)
                    except Exception as e:
                        st.warning("⚠️ Erro ao ordenar dados.")
                    
                    # Formatar valores monetários para exibição
                    df_display = df_filtrado.copy()
                    colunas_monetarias = ["Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro"]
                    for col in colunas_monetarias:
                        if col in df_display.columns:
                            df_display[col] = df_display[col].apply(lambda x: format_currency(x) if pd.notnull(x) and x != 0 else "R$ 0,00")
                    
                    st.dataframe(df_display, use_container_width=True)
                    
                    # Estatísticas do período
                    st.markdown("---")
                    st.markdown("### 📈 Estatísticas do Período")
                    
                    # Converter colunas numéricas para cálculos
                    for col in colunas_monetarias:
                        if col in df_filtrado.columns:
                            df_filtrado[col] = pd.to_numeric(df_filtrado[col], errors="coerce").fillna(0)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        total_operacoes = len(df_filtrado)
                        st.metric("Total de Operações", total_operacoes)
                    
                    with col2:
                        total_valor_bruto = df_filtrado["Valor_Bruto"].sum()
                        st.metric("Valor Bruto Total", format_currency(total_valor_bruto))
                    
                    with col3:
                        total_taxas = df_filtrado["Taxa_Cliente"].sum()
                        st.metric("Total em Taxas", format_currency(total_taxas))
                    
                    with col4:
                        total_liquido = df_filtrado["Valor_Liquido"].sum()
                        st.metric("Valor Líquido Total", format_currency(total_liquido))
                
                else:
                    st.info("📊 Nenhuma operação encontrada para os filtros selecionados.")
            
            else:
                st.info("📊 Nenhuma operação registrada.")
        
        except Exception as e:
            st.error(f"❌ Erro ao carregar histórico: {str(e)}")

# ===== FECHAMENTO DIÁRIO =====

def render_fechamento_diario_simplificado(spreadsheet):
    """Renderiza fechamento diário do caixa interno"""
    st.subheader("🗓️ Fechamento Diário do Caixa Interno")

    try:
        # Cabeçalhos para fechamento
        HEADERS_FECHAMENTO_CAIXA = [
            "Data_Fechamento", "Operador", "Saldo_Dia_Anterior", 
            "Total_Saques_Cartao", "Total_Trocas_Cheque", "Total_Suprimentos",
            "Saldo_Calculado_Dia", "Dinheiro_Contado_Gaveta", "Diferenca_Caixa",
            "Observacoes_Fechamento"
        ]

        # Obter data de hoje e de ontem
        hoje = obter_date_brasilia()
        ontem = hoje - timedelta(days=1)

        # 1. Buscar Saldo do Dia Anterior
        saldo_dia_anterior = 0.0
        try:
            fechamentos_data = buscar_dados(spreadsheet, "Fechamento_Diario_Caixa_Interno")
            if fechamentos_data:
                df_fechamentos = pd.DataFrame(fechamentos_data)
                df_fechamentos["Data_Fechamento"] = pd.to_datetime(df_fechamentos["Data_Fechamento"], errors='coerce').dt.date
                df_fechamentos["Saldo_Calculado_Dia"] = pd.to_numeric(df_fechamentos["Saldo_Calculado_Dia"], errors='coerce').fillna(0)
                
                registro_anterior = df_fechamentos[df_fechamentos["Data_Fechamento"] == ontem]
                
                if not registro_anterior.empty:
                    saldo_dia_anterior = float(registro_anterior.iloc[0]["Saldo_Calculado_Dia"])
        except Exception as e:
            st.warning(f"⚠️ Erro ao buscar saldo do dia anterior: {e}")

        st.markdown(f"**Saldo do Caixa no final do dia anterior ({ontem.strftime('%d/%m/%Y')}):** {format_currency(saldo_dia_anterior)}")
        st.markdown("---")

        # 2. Buscar e processar operações do dia de hoje
        operacoes_data = buscar_dados(spreadsheet, "Operacoes_Caixa")
        if not operacoes_data:
            st.info("📊 Nenhuma operação registrada para o dia de hoje.")
            operacoes_hoje = pd.DataFrame()
        else:
            operacoes_data_normalizada = normalizar_dados_inteligente(operacoes_data)
            df_operacoes = pd.DataFrame(operacoes_data_normalizada)
            for col in ["Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro"]:
                if col in df_operacoes.columns:
                    df_operacoes[col] = pd.to_numeric(df_operacoes[col], errors="coerce").fillna(0)
            df_operacoes["Data"] = pd.to_datetime(df_operacoes["Data"], errors="coerce").dt.date
            df_operacoes.dropna(subset=["Data"], inplace=True)
            operacoes_hoje = df_operacoes[df_operacoes["Data"] == hoje]

        # 3. Calcular Totais do Dia
        tipos_saque_cartao = ["Saque Cartão Débito", "Saque Cartão Crédito"]
        tipos_troca_cheque = ["Cheque à Vista", "Cheque Pré-datado", "Cheque com Taxa Manual"]
        tipo_suprimento = "Suprimento"

        total_saques_cartao = operacoes_hoje[operacoes_hoje["Tipo_Operacao"].isin(tipos_saque_cartao)]["Valor_Liquido"].sum()
        total_trocas_cheque = operacoes_hoje[operacoes_hoje["Tipo_Operacao"].isin(tipos_troca_cheque)]["Valor_Liquido"].sum()
        total_suprimentos = operacoes_hoje[operacoes_hoje["Tipo_Operacao"] == tipo_suprimento]["Valor_Bruto"].sum()

        saldo_calculado_dia = saldo_dia_anterior + total_suprimentos - (total_saques_cartao + total_trocas_cheque)

        st.markdown("---")
        st.markdown("#### Resumo do Dia")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Saques Cartão", format_currency(total_saques_cartao))
        with col2:
            st.metric("Total Trocas Cheque", format_currency(total_trocas_cheque))
        with col3:
            st.metric("Total Suprimentos", format_currency(total_suprimentos))
        
        st.markdown(f"**Saldo Calculado para Hoje ({hoje.strftime('%d/%m/%Y')}):** {format_currency(saldo_calculado_dia)}")
        st.markdown("---")

        # 4. Formulário para registrar o fechamento
        with st.form("form_fechamento_caixa_simplificado", clear_on_submit=True):
            st.markdown("#### Registrar Fechamento Diário")
            dinheiro_contado = st.number_input("Dinheiro Contado na Gaveta (R$)", min_value=0.0, step=10.0, format="%.2f")
            observacoes_fechamento = st.text_area("Observações do Fechamento (Opcional)")

            diferenca = dinheiro_contado - saldo_calculado_dia
            
            if dinheiro_contado > 0:
                st.markdown(f"**Diferença:** {format_currency(diferenca)}")
                
                if abs(diferenca) > 10:
                    st.warning(f"⚠️ Diferença significativa detectada: {format_currency(diferenca)}")

            if st.form_submit_button("💾 Salvar Fechamento", use_container_width=True):
                try:
                    worksheet = get_or_create_worksheet(spreadsheet, "Fechamento_Diario_Caixa_Interno", HEADERS_FECHAMENTO_CAIXA)
                    
                    if worksheet:
                        novo_fechamento = [
                            hoje.strftime("%Y-%m-%d"),
                            st.session_state.nome_usuario,
                            format_currency_us(saldo_dia_anterior),
                            format_currency_us(total_saques_cartao),
                            format_currency_us(total_trocas_cheque),
                            format_currency_us(total_suprimentos),
                            format_currency_us(saldo_calculado_dia),
                            format_currency_us(dinheiro_contado),
                            format_currency_us(diferenca),
                            observacoes_fechamento
                        ]
                        
                        if salvar_operacao_segura(worksheet, novo_fechamento):
                            st.success("✅ Fechamento diário registrado com sucesso!")
                            st.cache_data.clear()
                
                except Exception as e:
                    st.error(f"❌ Erro ao salvar fechamento: {str(e)}")

    except Exception as e:
        st.error(f"❌ Erro ao carregar fechamento diário: {str(e)}")

# ===== FUNÇÃO PRINCIPAL =====

def main():
    """Função principal da aplicação"""
    
    # Verificar se está logado
    if "logado" not in st.session_state:
        st.session_state.logado = False
    
    if not st.session_state.logado:
        render_login()
        return
    
    # Conectar ao Google Sheets
    spreadsheet = conectar_google_sheets()
    
    if spreadsheet:
        st.success("🔗 Conectado via Streamlit Secrets (Deploy)")
    else:
        st.error("❌ Não foi possível conectar ao Google Sheets. Verifique as credenciais.")
        return
    
    # Sidebar com navegação
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 1rem;">
            <h3 style="color: white; margin: 0;">📋 Menu Principal</h3>
            <p style="color: rgba(255,255,255,0.8); margin: 0.5rem 0 0 0;">✅ {st.session_state.perfil}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Opções baseadas no perfil
        if st.session_state.perfil == "Gerente":
            opcoes_menu = {
                "📊 Dashboard Caixa": "dashboard_caixa",
                "💳 Operações Caixa": "operacoes_caixa",
                "🏦 Gestão do Cofre": "gestao_cofre",
                "🗓️ Fechamento Diário Caixa Interno": "fechamento_diario_caixa_interno"
            }
        elif st.session_state.perfil == "Operador Caixa":
            opcoes_menu = {
                "📊 Dashboard Caixa": "dashboard_caixa",
                "💳 Operações Caixa": "operacoes_caixa",
                "🗓️ Fechamento Diário Caixa Interno": "fechamento_diario_caixa_interno"
            }
        else:  # Operador Lotérica
            opcoes_menu = {
                "📊 Dashboard Caixa": "dashboard_caixa",
                "💳 Operações Caixa": "operacoes_caixa"
            }
        
        # Renderizar botões do menu
        for nome_opcao, chave_opcao in opcoes_menu.items():
            if st.button(nome_opcao, use_container_width=True):
                st.session_state.pagina_atual = chave_opcao
        
        st.markdown("---")
        
        if st.button("🚪 Sair do Sistema", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    # Renderizar página atual
    pagina_atual = st.session_state.get("pagina_atual", "dashboard_caixa")
    
    # Header principal
    st.markdown("""
    <div style="text-align: center; padding: 1rem; margin-bottom: 2rem;">
        <h1>👑 Dashboard Gerencial - Sistema Unificado</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Renderizar conteúdo baseado na página
    if pagina_atual == "dashboard_caixa":
        render_dashboard_caixa(spreadsheet)
    elif pagina_atual == "operacoes_caixa":
        render_operacoes_caixa(spreadsheet)
    elif pagina_atual == "gestao_cofre":
        render_cofre(spreadsheet)
    elif pagina_atual == "fechamento_diario_caixa_interno":
        render_fechamento_diario_simplificado(spreadsheet)

if __name__ == "__main__":
    main()

