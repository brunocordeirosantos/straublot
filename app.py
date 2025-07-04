
def aplicar_filtro_por_data(df, coluna_data, data_inicio, data_fim):
    df[coluna_data] = pd.to_datetime(df[coluna_data], errors='coerce').dt.date
    return df[(df[coluna_data] >= data_inicio) & (df[coluna_data] <= data_fim)]

import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
import os
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go
from decimal import Decimal, ROUND_HALF_UP
import hashlib

# Importar pytz com tratamento de erro
try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False
    st.warning("⚠️ Biblioteca pytz não encontrada. Usando horário UTC.")

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
    # Fallback para horário local
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
    # Fallback para data local
    return datetime.now().strftime("%Y-%m-%d")

def obter_datetime_brasilia():
    """Retorna datetime atual no fuso horário de Brasília"""
    if PYTZ_AVAILABLE:
        try:
            tz_brasilia = pytz.timezone("America/Sao_Paulo")
            return datetime.now(tz_brasilia)
        except:
            pass
    # Fallback para datetime local
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
    # Fallback para date local
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
    /* Importar fonte Inter */
    @import url("https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap");
    
    /* Aplicar fonte globalmente */
    html, body, [class*="css"] {
        font-family: "Inter", sans-serif;
    }
    
    /* Estilo para botões principais */
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
        height: 3.5rem;
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* Estilo para botões de sucesso */
    .success-button > button {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    /* Estilo para botões de simulação */
    .simulate-button > button {
        background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    /* Cards de métricas */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin: 1rem 0;
        border: 1px solid #f0f0f0;
    }
    
    .metric-card h3 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
        color: white;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    }
    
    .metric-card p {
        margin: 0.5rem 0 0 0;
        font-size: 0.9rem;
        color: white;
        font-weight: 500;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
    }
    
    /* Estilo para selectbox */
    .stSelectbox > div > div {
        border-radius: 8px;
        border: 2px solid #e0e0e0;
        transition: all 0.3s ease;
    }
    
    .stSelectbox > div > div:focus-within {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Estilo para inputs */
    .stNumberInput > div > div > input,
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 8px;
        border: 2px solid #e0e0e0;
        transition: all 0.3s ease;
    }
    
    .stNumberInput > div > div > input:focus,
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
        border-radius: 10px;
        background-color: #f8f9fa;
        border: 2px solid transparent;
        transition: all 0.3s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-color: #667eea;
    }
    
    /* Alertas customizados */
    .alert-success {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        color: #155724;
    }
    
    .alert-info {
        background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
        border: 1px solid #bee5eb;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        color: #0c5460;
    }
    
    /* Responsividade */
    @media (max-width: 768px) {
        .metric-card h3 {
            font-size: 1.5rem;
        }
        
        .stButton > button {
            height: 3rem;
            font-size: 0.9rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Função para conectar ao Google Sheets
@st.cache_resource
def conectar_google_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Primeiro tenta usar Streamlit Secrets (para deploy)
        try:
            credentials_dict = {
                "type": st.secrets["gcp_service_account"]["type"],
                "project_id": st.secrets["gcp_service_account"]["project_id"],
                "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
                "private_key": st.secrets["gcp_service_account"]["private_key"],
                "client_email": st.secrets["gcp_service_account"]["client_email"],
                "client_id": st.secrets["gcp_service_account"]["client_id"],
                "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
                "token_uri": st.secrets["gcp_service_account"]["token_uri"],
                "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
                "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"]
            }
            creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
            st.success("🌐 Conectado via Streamlit Secrets (Deploy)")
            
        except (KeyError, FileNotFoundError):
            # Fallback para arquivo local
            try:
                creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
                st.success("💻 Conectado via arquivo local")
            except FileNotFoundError:
                st.error("❌ Arquivo credentials.json não encontrado")
                st.info("📋 Para usar localmente, adicione o arquivo credentials.json na pasta do projeto")
                return None
        
        client = gspread.authorize(creds)
        return client.open("Lotericabasededados")
    except Exception as e:
        st.error(f"Erro ao conectar com Google Sheets: {str(e)}")
        return None
# Função para criar ou obter worksheet
def get_or_create_worksheet(spreadsheet, sheet_name, headers):
    try:
        if spreadsheet is None:
            # Modo demo - retorna None
            return None
        
        worksheet = spreadsheet.worksheet(sheet_name)
        return worksheet
    except:
        if spreadsheet is None:
            return None
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="20")
        worksheet.append_row(headers)
        return worksheet
# Função para buscar dados do Google Sheets
@st.cache_data(ttl=60)
def buscar_dados(_spreadsheet, sheet_name):
    try:
        if _spreadsheet is None:
            st.warning("⚠️ Sem conexão com Google Sheets")
            return []
        
        worksheet = _spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return data
    except Exception as e:
        st.warning(f"⚠️ Erro ao buscar dados de {sheet_name}: {str(e)}")
        return []

# Função para normalizar dados com detecção inteligente
def normalizar_dados_inteligente(dados):
    """
    Função inteligente que detecta automaticamente padrões de erro nos dados
    e aplica a correção mais adequada baseada em validação matemática
    """
    dados_corrigidos = []
    
    for registro in dados:
        registro_corrigido = registro.copy()
        
        # Verificar se tem os campos necessários
        if not all(campo in registro for campo in ["Valor_Bruto", "Taxa_Cliente", "Valor_Liquido"]):
            dados_corrigidos.append(registro_corrigido)
            continue
            
        try:
            valor_bruto = float(registro["Valor_Bruto"])
            taxa_cliente = float(registro["Taxa_Cliente"])
            valor_liquido = float(registro["Valor_Liquido"])
            
            # Se valor bruto é 0, pular validação
            if valor_bruto == 0:
                dados_corrigidos.append(registro_corrigido)
                continue
            
            # Testar diferentes fatores de correção
            fatores_teste = [1, 0.01, 0.1, 10, 100]
            melhor_fator_taxa = 1
            melhor_fator_liquido = 1
            menor_erro = float("inf")
            
            for fator_taxa in fatores_teste:
                for fator_liquido in fatores_teste:
                    taxa_teste = taxa_cliente * fator_taxa
                    liquido_teste = valor_liquido * fator_liquido
                    
                    # Validações básicas
                    if taxa_teste > valor_bruto * 0.5:  # Taxa não pode ser maior que 50%
                        continue
                    if liquido_teste > valor_bruto:  # Líquido não pode ser maior que bruto
                        continue
                    if liquido_teste <= 0:  # Líquido deve ser positivo
                        continue
                    
                    # Calcular erro matemático: Valor_Liquido deveria ser Valor_Bruto - Taxa_Cliente
                    valor_esperado = valor_bruto - taxa_teste
                    erro = abs(liquido_teste - valor_esperado)
                    
                    if erro < menor_erro:
                        menor_erro = erro
                        melhor_fator_taxa = fator_taxa
                        melhor_fator_liquido = fator_liquido
            
            # Aplicar correções se necessário
            if melhor_fator_taxa != 1:
                registro_corrigido["Taxa_Cliente"] = taxa_cliente * melhor_fator_taxa
                
            if melhor_fator_liquido != 1:
                registro_corrigido["Valor_Liquido"] = valor_liquido * melhor_fator_liquido
            
            # Corrigir outros campos relacionados se existirem
            if "Taxa_Banco" in registro and melhor_fator_taxa != 1:
                taxa_banco = float(registro.get("Taxa_Banco", 0))
                registro_corrigido["Taxa_Banco"] = taxa_banco * melhor_fator_taxa
                
            if "Lucro" in registro and melhor_fator_taxa != 1:
                lucro = float(registro.get("Lucro", 0))
                registro_corrigido["Lucro"] = lucro * melhor_fator_taxa
                
        except (ValueError, TypeError):
            # Se houver erro na conversão, manter dados originais
            pass
            
        dados_corrigidos.append(registro_corrigido)
    
    return dados_corrigidos

# Função para limpar cache forçadamente
def limpar_cache_forcado():
    st.cache_data.clear()
    if "simulacao_atual" in st.session_state:
        del st.session_state.simulacao_atual

# Função de debug para valores
def debug_valores(dados, titulo="Debug"):
    if st.checkbox(f"🔍 Debug - {titulo}"):
        st.write("**Dados brutos:**")
        for i, registro in enumerate(dados[:3]):  # Mostrar apenas 3 primeiros
            st.write(f"Registro {i+1}:")
            for campo in ["Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro"]:
                if campo in registro:
                    st.write(f"  {campo}: {registro[campo]} (tipo: {type(registro[campo])})")

# Funções de cálculo corrigidas
def calcular_taxa_cartao_debito(valor):
    valor_dec = Decimal(str(valor))
    taxa_cliente = (valor_dec * Decimal("0.01")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)  # 1% sobre o valor
    taxa_banco = Decimal("1.00")   # Taxa fixa de R$ 1,00 que o banco cobra da empresa
    lucro = taxa_cliente - taxa_banco  # Lucro = taxa cliente - taxa banco
    valor_liquido = valor_dec - taxa_cliente
    
    return {
        "taxa_cliente": float(taxa_cliente),
        "taxa_banco": float(taxa_banco),
        "lucro": float(max(Decimal("0"), lucro)),  # Lucro não pode ser negativo
        "valor_liquido": float(valor_liquido)
    }

def calcular_taxa_cartao_credito(valor):
    valor_dec = Decimal(str(valor))
    taxa_cliente = (valor_dec * Decimal("0.0533")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    taxa_banco = (valor_dec * Decimal("0.0433")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    lucro = taxa_cliente - taxa_banco
    valor_liquido = valor_dec - taxa_cliente
    
    return {
        "taxa_cliente": float(taxa_cliente),
        "taxa_banco": float(taxa_banco), 
        "lucro": float(max(Decimal("0"), lucro)), 
        "valor_liquido": float(valor_liquido)
    }

def calcular_taxa_cheque_vista(valor):
    valor_dec = Decimal(str(valor))
    taxa_cliente = (valor_dec * Decimal("0.02")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    taxa_banco = Decimal("0.00")
    lucro = taxa_cliente
    valor_liquido = valor_dec - taxa_cliente
    
    return {
        "taxa_cliente": float(taxa_cliente),
        "taxa_banco": float(taxa_banco),
        "lucro": float(lucro),
        "valor_liquido": float(valor_liquido)
    }

def calcular_taxa_cheque_pre_datado(valor, dias):
    valor_dec = Decimal(str(valor))
    taxa_base = valor_dec * Decimal("0.02")  # 2% base
    taxa_adicional = valor_dec * Decimal("0.0033") * Decimal(str(dias))  # 0.33% por dia
    taxa_cliente = (taxa_base + taxa_adicional).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    taxa_banco = Decimal("0.00")
    lucro = taxa_cliente
    valor_liquido = valor_dec - taxa_cliente
    
    return {
        "taxa_cliente": float(taxa_cliente),
        "taxa_banco": float(taxa_banco),
        "lucro": float(lucro),
        "valor_liquido": float(valor_liquido)
    }

def calcular_taxa_cheque_manual(valor, taxa_percentual):
    valor_dec = Decimal(str(valor))
    taxa_perc_dec = Decimal(str(taxa_percentual)) / Decimal("100")
    taxa_cliente = (valor_dec * taxa_perc_dec).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    taxa_banco = Decimal("0.00")
    lucro = taxa_cliente
    valor_liquido = valor_dec - taxa_cliente
    
    return {
        "taxa_cliente": float(taxa_cliente),
        "taxa_banco": float(taxa_banco),
        "lucro": float(lucro),
        "valor_liquido": float(valor_liquido)
    }

# Sistema de autenticação
def verificar_login():
    if "logado" not in st.session_state:
        st.session_state.logado = False
    
    if not st.session_state.logado:
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <h1 style="color: #667eea; margin-bottom: 2rem;">🏪 Sistema Unificado</h1>
            <h3 style="color: #666; margin-bottom: 3rem;">Lotérica & Caixa Interno</h3>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                st.markdown("### 🔐 Acesso ao Sistema")
                
                tipo_usuario = st.selectbox(
                    "👤 Tipo de Usuário",
                    ["👑 Gerente", "🎰 Operador Lotérica", "💳 Operador Caixa"]
                )
                
                senha = st.text_input("🔑 Senha", type="password")
                
                col_login1, col_login2 = st.columns(2)
                with col_login1:
                    login_button = st.form_submit_button("🚀 Acessar Sistema", use_container_width=True)
                with col_login2:
                    help_button = st.form_submit_button("ℹ️ Ajuda", use_container_width=True)
                
                if help_button:
                    st.info("""
                    **Credenciais de Acesso:**
                    - 👑 Gerente: gerente123
                    - 🎰 Operador Lotérica: loterica123  
                    - 💳 Operador Caixa: caixa123
                    """)
                
                if login_button:
                    senhas = {
                        "👑 Gerente": "gerente123",
                        "🎰 Operador Lotérica": "loterica123",
                        "💳 Operador Caixa": "caixa123"
                    }
                    
                    if senha == senhas.get(tipo_usuario):
                        st.session_state.logado = True
                        st.session_state.tipo_usuario = tipo_usuario
                        st.session_state.nome_usuario = tipo_usuario.split(" ", 1)[1]
                        st.success(f"✅ Login realizado com sucesso! Bem-vindo, {st.session_state.nome_usuario}!")
                        st.rerun()
                    else:
                        st.error("❌ Senha incorreta!")
        return False
    return True

# Função para fechamento da lotérica
def render_fechamento_loterica(spreadsheet):
    st.subheader("📋 Fechamento de Caixa Lotérica")
    
    try:
        HEADERS_FECHAMENTO = [
            "Data_Fechamento", "PDV", "Operador", 
            "Qtd_Compra_Bolao", "Custo_Unit_Bolao", "Total_Compra_Bolao",
            "Qtd_Compra_Raspadinha", "Custo_Unit_Raspadinha", "Total_Compra_Raspadinha",
            "Qtd_Compra_LoteriaFederal", "Custo_Unit_LoteriaFederal", "Total_Compra_LoteriaFederal",
            "Qtd_Venda_Bolao", "Preco_Unit_Bolao", "Total_Venda_Bolao",
            "Qtd_Venda_Raspadinha", "Preco_Unit_Raspadinha", "Total_Venda_Raspadinha",
            "Qtd_Venda_LoteriaFederal", "Preco_Unit_LoteriaFederal", "Total_Venda_LoteriaFederal",
            "Movimentacao_Cielo", "Pagamento_Premios", "Vales_Despesas", 
            "Retirada_Cofre", "Retirada_CaixaInterno", "Dinheiro_Gaveta_Final",
            "Saldo_Anterior", "Saldo_Final_Calculado", "Diferenca_Caixa"
        ]
        
        with st.form("form_fechamento_pdv", clear_on_submit=False):
            st.markdown("#### Lançar Fechamento Diário do PDV")
            
            col1, col2 = st.columns(2)
            with col1:
                pdv_selecionado = st.selectbox("Selecione o PDV", ["PDV 1", "PDV 2"])
            with col2:
                data_fechamento = st.date_input("Data do Fechamento", obter_date_brasilia())
            
            # Buscar saldo anterior
            sheet_name = f"Fechamentos_{pdv_selecionado.replace(" ", "")}"
            fechamentos_data = buscar_dados(spreadsheet, sheet_name)
            df_fechamentos = pd.DataFrame(fechamentos_data)
            
            saldo_anterior = Decimal("0")
            if not df_fechamentos.empty:
                try:
                    df_fechamentos["Data_Fechamento"] = pd.to_datetime(df_fechamentos["Data_Fechamento"], errors="coerce").dt.date
                    df_fechamentos["Saldo_Final_Calculado"] = pd.to_numeric(df_fechamentos["Saldo_Final_Calculado"], errors="coerce").fillna(0)
                    
                    registro_anterior = df_fechamentos[df_fechamentos["Data_Fechamento"] == data_anterior]
                    
                    if not registro_anterior.empty:
                        saldo_anterior = Decimal(str(registro_anterior.iloc[0]["Saldo_Final_Calculado"]))
                except Exception as e:
                    st.warning("⚠️ Erro ao calcular saldo anterior. Usando saldo zero.")
            
            st.info(f"💰 Saldo anterior ({data_fechamento - timedelta(days=1)}): R$ {saldo_anterior:,.2f}")
            
            # Seção de Compras
            st.markdown("### 🛒 Compras do Dia")
            col_comp1, col_comp2, col_comp3 = st.columns(3)
            
            with col_comp1:
                st.markdown("**Bolão**")
                qtd_comp_bolao = st.number_input("Quantidade", min_value=0, step=1, key="qtd_comp_bolao")
                custo_unit_bolao = st.number_input("Custo Unitário (R$)", min_value=0.0, step=0.01, key="custo_bolao")
                total_comp_bolao = qtd_comp_bolao * custo_unit_bolao
                st.write(f"Total: R$ {total_comp_bolao:.2f}")
            
            with col_comp2:
                st.markdown("**Raspadinha**")
                qtd_comp_rasp = st.number_input("Quantidade", min_value=0, step=1, key="qtd_comp_rasp")
                custo_unit_rasp = st.number_input("Custo Unitário (R$)", min_value=0.0, step=0.01, key="custo_rasp")
                total_comp_rasp = qtd_comp_rasp * custo_unit_rasp
                st.write(f"Total: R$ {total_comp_rasp:.2f}")
            
            with col_comp3:
                st.markdown("**Loteria Federal**")
                qtd_comp_fed = st.number_input("Quantidade", min_value=0, step=1, key="qtd_comp_fed")
                custo_unit_fed = st.number_input("Custo Unitário (R$)", min_value=0.0, step=0.01, key="custo_fed")
                total_comp_fed = qtd_comp_fed * custo_unit_fed
                st.write(f"Total: R$ {total_comp_fed:.2f}")
            
            # Seção de Vendas
            st.markdown("### 💰 Vendas do Dia")
            col_vend1, col_vend2, col_vend3 = st.columns(3)
            
            with col_vend1:
                st.markdown("**Bolão**")
                qtd_vend_bolao = st.number_input("Quantidade", min_value=0, step=1, key="qtd_vend_bolao")
                preco_unit_bolao = st.number_input("Preço Unitário (R$)", min_value=0.0, step=0.01, key="preco_bolao")
                total_vend_bolao = qtd_vend_bolao * preco_unit_bolao
                st.write(f"Total: R$ {total_vend_bolao:.2f}")
            
            with col_vend2:
                st.markdown("**Raspadinha**")
                qtd_vend_rasp = st.number_input("Quantidade", min_value=0, step=1, key="qtd_vend_rasp")
                preco_unit_rasp = st.number_input("Preço Unitário (R$)", min_value=0.0, step=0.01, key="preco_rasp")
                total_vend_rasp = qtd_vend_rasp * preco_unit_rasp
                st.write(f"Total: R$ {total_vend_rasp:.2f}")
            
            with col_vend3:
                st.markdown("**Loteria Federal**")
                qtd_vend_fed = st.number_input("Quantidade", min_value=0, step=1, key="qtd_vend_fed")
                preco_unit_fed = st.number_input("Preço Unitário (R$)", min_value=0.0, step=0.01, key="preco_fed")
                total_vend_fed = qtd_vend_fed * preco_unit_fed
                st.write(f"Total: R$ {total_vend_fed:.2f}")
            
            # Outras movimentações
            st.markdown("### 🔄 Outras Movimentações")
            col_mov1, col_mov2 = st.columns(2)
            
            with col_mov1:
                movimentacao_cielo = st.number_input("Movimentação Cielo (R$)", step=0.01)
                pagamento_premios = st.number_input("Pagamento de Prêmios (R$)", step=0.01)
                vales_despesas = st.number_input("Vales e Despesas (R$)", step=0.01)
            
            with col_mov2:
                retirada_cofre = st.number_input("Retirada para Cofre (R$)", step=0.01)
                retirada_caixa_interno = st.number_input("Retirada para Caixa Interno (R$)", step=0.01)
                dinheiro_gaveta = st.number_input("Dinheiro na Gaveta (R$)", step=0.01)
            
            # Cálculos automáticos
            total_entradas = total_vend_bolao + total_vend_rasp + total_vend_fed + movimentacao_cielo
            total_saidas = total_comp_bolao + total_comp_rasp + total_comp_fed + pagamento_premios + vales_despesas + retirada_cofre + retirada_caixa_interno
            
            saldo_calculado = saldo_anterior + total_entradas - total_saidas
            diferenca_caixa = dinheiro_gaveta - saldo_calculado
            
            # Resumo
            st.markdown("### 📊 Resumo do Fechamento")
            col_res1, col_res2, col_res3 = st.columns(3)
            
            with col_res1:
                st.metric("Total Entradas", f"R$ {total_entradas:.2f}")
                st.metric("Saldo Anterior", f"R$ {saldo_anterior:.2f}")
            
            with col_res2:
                st.metric("Total Saídas", f"R$ {total_saidas:.2f}")
                st.metric("Saldo Calculado", f"R$ {saldo_calculado:.2f}")
            
            with col_res3:
                st.metric("Dinheiro na Gaveta", f"R$ {dinheiro_gaveta:.2f}")
                
                if diferenca_caixa == 0:
                    st.success(f"✅ Caixa Fechado: R$ {diferenca_caixa:.2f}")
                elif diferenca_caixa > 0:
                    st.warning(f"⚠️ Sobra: R$ {diferenca_caixa:.2f}")
                else:
                    st.error(f"❌ Falta: R$ {abs(diferenca_caixa):.2f}")
            
            # Salvar fechamento
            if st.form_submit_button("💾 Salvar Fechamento", use_container_width=True):
                try:
                    fechamento_sheet = get_or_create_worksheet(spreadsheet, sheet_name, HEADERS_FECHAMENTO)
                    
                    novo_fechamento = [
                        str(data_fechamento), pdv_selecionado, st.session_state.nome_usuario,
                        qtd_comp_bolao, custo_unit_bolao, total_comp_bolao,
                        qtd_comp_rasp, custo_unit_rasp, total_comp_rasp,
                        qtd_comp_fed, custo_unit_fed, total_comp_fed,
                        qtd_vend_bolao, preco_unit_bolao, total_vend_bolao,
                        qtd_vend_rasp, preco_unit_rasp, total_vend_rasp,
                        qtd_vend_fed, preco_unit_fed, total_vend_fed,
                        movimentacao_cielo, pagamento_premios, vales_despesas,
                        retirada_cofre, retirada_caixa_interno, dinheiro_gaveta,
                        float(saldo_anterior), float(saldo_calculado), float(diferenca_caixa)
                    ]
                    
                    fechamento_sheet.append_row(novo_fechamento)
                    st.success(f"✅ Fechamento do {pdv_selecionado} salvo com sucesso!")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"❌ Erro ao salvar fechamento: {str(e)}")
    
    except Exception as e:
        st.error(f"❌ Erro ao carregar fechamento da lotérica: {str(e)}")
        st.info("🔄 Tente recarregar a página ou verifique a conexão com o Google Sheets.")

# Função principal do dashboard do caixa
def render_dashboard_caixa(spreadsheet):
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
        
        # Converter colunas numéricas com tratamento de erro
        for col in ["Valor_Bruto", "Valor_Liquido", "Taxa_Cliente", "Taxa_Banco", "Lucro"]:
            if col in df_operacoes.columns:
                df_operacoes[col] = pd.to_numeric(df_operacoes[col], errors="coerce").fillna(0)
        
        # Calcular métricas
        total_suprimentos = df_operacoes[df_operacoes["Tipo_Operacao"] == "Suprimento"]["Valor_Bruto"].sum()
        tipos_de_saida = ["Saque Cartão Débito", "Saque Cartão Crédito", "Troca Cheque à Vista", "Troca Cheque Pré-datado", "Troca Cheque com Taxa Manual"]
        total_saques_liquidos = df_operacoes[df_operacoes["Tipo_Operacao"].isin(tipos_de_saida)]["Valor_Liquido"].sum()
        
        # Saldo do caixa (saldo inicial + suprimentos - saques líquidos)
        saldo_inicial = 0  # Saldo inicial configurado
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
                <h3>R$ {saldo_caixa:,.2f}</h3>
                <p>💰 Saldo do Caixa</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                <h3>R$ {valor_saque_hoje:,.2f}</h3>
                <p>💳 Valor Saque Hoje</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                <h3>{operacoes_hoje_count}</h3>
                <p>📋 Operações Hoje</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            status_cor = "#38ef7d" if saldo_caixa > 2000 else "#f5576c"
            status_texto = "Normal" if saldo_caixa > 2000 else "Baixo"
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, {status_cor} 0%, {status_cor} 100%);">
                <h3>{status_texto}</h3>
                <p>🚦 Status Caixa</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Gráfico de resumo de operações
        st.subheader("📊 Resumo de Operações (Últimos 7 Dias)")
        
        try:
            df_operacoes["Data"] = pd.to_datetime(df_operacoes["Data"], errors="coerce")
            df_operacoes.dropna(subset=["Data"], inplace=True)
            
            # Converter datetime de Brasília para pandas datetime com tratamento de erro
            try:
                data_limite = obter_datetime_brasilia() - timedelta(days=7)
                data_limite_pandas = pd.to_datetime(data_limite.strftime("%Y-%m-%d"))
            except:
                # Fallback se houver erro
                data_limite_pandas = pd.to_datetime((datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"))
            
            df_recente = df_operacoes[df_operacoes["Data"] >= data_limite_pandas]
            
            if not df_recente.empty:
                resumo_por_tipo = df_recente.groupby("Tipo_Operacao")["Valor_Liquido"].sum().reset_index()
                
                fig = px.bar(
                    resumo_por_tipo, 
                    x="Tipo_Operacao", 
                    y="Valor_Liquido",
                    title="Valor Líquido por Tipo de Operação",
                    labels={
                        "Tipo_Operacao": "Tipo de Operação", 
                        "Valor_Liquido": "Valor Líquido Total (R$)"
                    },
                    color="Tipo_Operacao",
                    text_auto=".2f"
                )
                fig.update_layout(
                    showlegend=False,
                    height=400,
                    font=dict(family="Inter, sans-serif")
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📊 Nenhuma operação nos últimos 7 dias para exibir no gráfico.")
        except Exception as e:
            st.warning("⚠️ Erro ao carregar gráfico. Dados podem estar inconsistentes.")
        
        # Alertas de saldo
        if saldo_caixa < 1000:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%); padding: 1rem; border-radius: 10px; color: white; margin: 1rem 0;">
                🚨 <strong>Atenção!</strong> Saldo do caixa está muito baixo. Solicite suprimento urgente.
            </div>
            """, unsafe_allow_html=True)
        elif saldo_caixa < 2000:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #ffa726 0%, #ff9800 100%); padding: 1rem; border-radius: 10px; color: white; margin: 1rem 0;">
                ⚠️ <strong>Aviso:</strong> Saldo do caixa está baixo. Considere solicitar suprimento.
            </div>
            """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar dashboard: {str(e)}")
        st.info("🔄 Tente recarregar a página ou verifique a conexão com o Google Sheets.")

# Função melhorada para gestão do cofre com interface dinâmica
def render_cofre(spreadsheet):
    st.subheader("🏦 Gestão do Cofre")
    
    try:
        # Headers para o cofre
        HEADERS_COFRE = ["Data", "Hora", "Operador", "Tipo_Transacao", "Valor", "Destino_Origem", "Observacoes"]
        
        # Buscar dados do cofre
        cofre_data = buscar_dados(spreadsheet, "Operacoes_Cofre")
        df_cofre = pd.DataFrame(cofre_data)
        
        # Calcular saldo do cofre
        saldo_cofre = Decimal("0")
        if not df_cofre.empty and "Tipo_Transacao" in df_cofre.columns and "Valor" in df_cofre.columns:
            df_cofre["Valor"] = pd.to_numeric(df_cofre["Valor"], errors="coerce").fillna(0)
            df_cofre["Tipo_Transacao"] = df_cofre["Tipo_Transacao"].astype(str)
            
            entradas = df_cofre[df_cofre["Tipo_Transacao"] == "Entrada no Cofre"]["Valor"].sum()
            saidas = df_cofre[df_cofre["Tipo_Transacao"] == "Saída do Cofre"]["Valor"].sum()
            saldo_cofre = Decimal(str(entradas)) - Decimal(str(saidas))
        
        # Exibir saldo do cofre
        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);">
            <h3>R$ {saldo_cofre:,.2f}</h3>
            <p>🔒 Saldo Atual do Cofre</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Tabs para organizar a interface
        tab1, tab2 = st.tabs(["➕ Registrar Movimentação", "📋 Histórico do Cofre"])
        
        with tab1:
            st.markdown("#### Nova Movimentação no Cofre")

            # --- NOVO CÓDIGO: Mover o selectbox para fora do formulário ---
            tipo_mov = st.selectbox(
                "Tipo de Movimentação",
                ["Entrada no Cofre", "Saída do Cofre"],
                key="tipo_mov_cofre_dinamico"  # Usar uma nova chave para evitar conflitos
            )

            with st.form("form_mov_cofre", clear_on_submit=True):
                # O tipo_mov já foi definido fora, então o usamos aqui dentro
                
                valor = st.number_input("Valor da Movimentação (R$)", min_value=0.01, step=100.0, key="valor_cofre")
                
                # O restante da lógica condicional permanece o mesmo
                destino_final = ""
                
                if tipo_mov == "Saída do Cofre":
                    tipo_saida = st.selectbox(
                        "Tipo de Saída:", 
                        ["Transferência para Caixa", "Pagamento de Despesa"],
                        key=f"tipo_saida_cofre_{tipo_mov}" # Chave dinâmica
                    )
                    
                    if tipo_saida == "Transferência para Caixa":
                        destino_caixa = st.selectbox(
                            "Transferir para:", 
                            ["Caixa Interno", "Caixa Lotérica"],
                            key=f"destino_caixa_cofre_{tipo_saida}" # Chave dinâmica
                        )
                        
                        if destino_caixa == "Caixa Lotérica":
                            destino_pdv = st.selectbox(
                                "Selecione o PDV:", 
                                ["PDV 1", "PDV 2"],
                                key=f"destino_pdv_cofre_{destino_caixa}" # Chave dinâmica
                            )
                            destino_final = f"{destino_caixa} - {destino_pdv}"
                        else: # Este else corresponde ao if da linha 740
                            destino_final = destino_caixa
                    else: # ESTE else CORRESPONDE AO if DA LINHA 733 (tipo_saida == "Transferência para Caixa")
                        destino_final = st.text_input(
                            "Descrição da Despesa (Ex: Aluguel, Fornecedor X)",
                            key="descricao_despesa_cofre"
                        )
                else: # Este else corresponde ao if da linha 725 (tipo_mov == "Saída do Cofre")
                    destino_final = st.text_input(
                        "Origem da Entrada (Ex: Banco, Sócio)",
                        key=f"origem_entrada_cofre_{tipo_mov}" # Chave dinâmica
                    )

                               
                observacoes = st.text_area("Observações Adicionais", key="obs_cofre")
                
                submitted = st.form_submit_button("💾 Salvar Movimentação", use_container_width=True)
                
                if submitted:
                    try:
                        # Salvar no Google Sheets
                        cofre_sheet = get_or_create_worksheet(spreadsheet, "Operacoes_Cofre", HEADERS_COFRE)
                        
                        nova_mov_cofre = [
                            obter_data_brasilia(), 
                            obter_horario_brasilia(), 
                            st.session_state.nome_usuario, 
                            tipo_mov, 
                            float(valor), 
                            destino_final, 
                            observacoes
                        ]
                        
                        cofre_sheet.append_row(nova_mov_cofre)
                        
                        # Se for saída para caixa interno, criar suprimento automaticamente
                        if tipo_mov == "Saída do Cofre" and destino_final == "Caixa Interno":
                            HEADERS_CAIXA = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]
                            caixa_sheet = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", HEADERS_CAIXA)
                            
                            nova_operacao_caixa = [
                                obter_data_brasilia(), 
                                obter_horario_brasilia(), 
                                st.session_state.nome_usuario, 
                                "Suprimento", 
                                "Sistema", 
                                "N/A", 
                                float(valor), 
                                0, 
                                0, 
                                float(valor), 
                                0, 
                                "Concluído", 
                                "", 
                                "0.00%", 
                                f"Transferência do Cofre para: {destino_final}"
                            ]
                            
                            caixa_sheet.append_row(nova_operacao_caixa)
                            st.success(f"✅ Saída de R$ {valor:,.2f} do cofre registrada e suprimento criado no Caixa Interno!")
                        
                        elif tipo_mov == "Saída do Cofre" and "Caixa Lotérica" in destino_final:
                            st.info(f"Saída para {destino_final} registrada. A integração de suprimento com o caixa da lotérica será implementada futuramente.")
                            st.success(f"✅ Movimentação de R$ {valor:,.2f} no cofre registrada com sucesso!")
                        else:
                            st.success(f"✅ Movimentação de R$ {valor:,.2f} no cofre registrada com sucesso!")
                        
                        # Limpar cache para atualizar dados
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"❌ Erro ao salvar movimentação: {str(e)}")
                
                if tipo_mov == "Saída do Cofre":
                    tipo_saida = st.selectbox(
                        "Tipo de Saída:", 
                        ["Transferência para Caixa", "Pagamento de Despesa"],
                        key=f"tipo_saida_cofre_{tipo_mov}" # Chave dinâmica
                    )
                    
                    if tipo_saida == "Transferência para Caixa":
                        destino_caixa = st.selectbox(
                            "Transferir para:", 
                            ["Caixa Interno", "Caixa Lotérica"],
                            key=f"destino_caixa_cofre_{tipo_saida}" # Chave dinâmica
                        )
                        
                        # --- CORREÇÃO DE INDENTAÇÃO AQUI ---
                        if destino_caixa == "Caixa Lotérica":
                            destino_pdv = st.selectbox(
                                "Selecione o PDV:", 
                                ["PDV 1", "PDV 2"],
                                key=f"destino_pdv_cofre_{destino_caixa}" # Chave dinâmica
                            )
                            destino_final = f"{destino_caixa} - {destino_pdv}"
                        else: # Este else corresponde ao if da linha 834
                            destino_final = destino_caixa
                    else: # Este else corresponde ao if da linha 826 (tipo_saida == "Transferência para Caixa")
                        destino_final = st.text_input(
                            "Descrição da Despesa (Ex: Aluguel, Fornecedor X)",
                            key="descricao_despesa_cofre"
                        )
                else: # Este else corresponde ao if da linha 819 (tipo_mov == "Saída do Cofre")
                    destino_final = st.text_input(
                        "Origem da Entrada (Ex: Banco, Sócio)",
                        key=f"origem_entrada_cofre_{tipo_mov}" # Chave dinâmica
                    )

                
                # Observações
                observacoes = st.text_area("Observações Adicionais", key="obs_cofre")
                
                # Botão de submissão
                submitted = st.form_submit_button("💾 Salvar Movimentação", use_container_width=True)
                
                if submitted:
                    try:
                        # Salvar no Google Sheets
                        cofre_sheet = get_or_create_worksheet(spreadsheet, "Operacoes_Cofre", HEADERS_COFRE)
                        
                        nova_mov_cofre = [
                            obter_data_brasilia(), 
                            obter_horario_brasilia(), 
                            st.session_state.nome_usuario, 
                            tipo_mov, 
                            float(valor), 
                            destino_final, 
                            observacoes
                        ]
                        
                        cofre_sheet.append_row(nova_mov_cofre)
                        
                        # Se for saída para caixa interno, criar suprimento automaticamente
                        if tipo_mov == "Saída do Cofre" and destino_final == "Caixa Interno":
                            HEADERS_CAIXA = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]
                            caixa_sheet = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", HEADERS_CAIXA)
                            
                            nova_operacao_caixa = [
                                obter_data_brasilia(), 
                                obter_horario_brasilia(), 
                                st.session_state.nome_usuario, 
                                "Suprimento", 
                                "Sistema", 
                                "N/A", 
                                float(valor), 
                                0, 
                                0, 
                                float(valor), 
                                0, 
                                "Concluído", 
                                "", 
                                "0.00%", 
                                f"Transferência do Cofre para: {destino_final}"
                            ]
                            
                            caixa_sheet.append_row(nova_operacao_caixa)
                            st.success(f"✅ Saída de R$ {valor:,.2f} do cofre registrada e suprimento criado no Caixa Interno!")
                        
                        elif tipo_mov == "Saída do Cofre" and "Caixa Lotérica" in destino_final:
                            st.info(f"Saída para {destino_final} registrada. A integração de suprimento com o caixa da lotérica será implementada futuramente.")
                            st.success(f"✅ Movimentação de R$ {valor:,.2f} no cofre registrada com sucesso!")
                        else:
                            st.success(f"✅ Movimentação de R$ {valor:,.2f} no cofre registrada com sucesso!")
                        
                        # Limpar cache para atualizar dados
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"❌ Erro ao salvar movimentação: {str(e)}")
        
        with tab2:
            st.markdown("#### Histórico de Movimentações")
            
            if not df_cofre.empty:
                # Ordenar por data e hora (mais recente primeiro)
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
        st.info("🔄 Tente recarregar a página ou verifique a conexão com o Google Sheets.")

# Função para operações do caixa interno
def render_operacoes_caixa(spreadsheet):

    if 'pagina_atual' in st.session_state and st.session_state.pagina_atual != 'operacoes_caixa':
        st.session_state.simulacao_atual = None

    st.subheader("💳 Operações do Caixa Interno")
    
    try:
        # Headers para operações do caixa
        HEADERS = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]
        
        # Tabs para organizar as operações
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["💳 Saque Cartão", "📄 Troca de Cheques", "🔄 Suprimento Caixa", "📊 Histórico", "🗓️ Fechamento Caixa Interno"])
        
        with tab1:
            st.markdown("### 💳 Saque com Cartão")
            
            with st.form("form_saque_cartao", clear_on_submit=False):
                # Campo de operador
                operador_selecionado = st.selectbox("👤 Operador Responsável", 
                    ["Bruna", "Karina", "Edson", "Robson", "Adiel", "Lucas", "Ana Paula", "Fernanda"])
                
                col1, col2 = st.columns(2)
                
                with col1:
                    tipo_cartao = st.selectbox("Tipo de Cartão", ["Débito", "Crédito"])
                    valor = st.number_input("Valor do Saque (R$)", min_value=0.01, step=50.0)
                    nome = st.text_input("Nome do Cliente (Opcional)")
                
                with col2:
                    cpf = st.text_input("CPF do Cliente (Opcional)")
                    observacoes = st.text_area("Observações")
                
                col_sim, col_conf = st.columns([1, 1])
                
                with col_sim:
                    simular = st.form_submit_button("🧮 Simular Operação", use_container_width=True)
                
                if simular and valor > 0:
                    try:
                        if tipo_cartao == "Débito":
                            calc = calcular_taxa_cartao_debito(valor)
                        else:
                            calc = calcular_taxa_cartao_credito(valor)
                        
                        st.markdown("---")
                        st.markdown(f"### ✅ Simulação - Cartão {tipo_cartao}")
                        
                        col_res1, col_res2 = st.columns(2)
                        with col_res1:
                            st.metric("Taxa Percentual", f"{(calc["taxa_cliente"]/valor)*100:.2f}%")
                            st.metric("Taxa em Valores", f"R$ {calc["taxa_cliente"]:,.2f}")
                        
                        with col_res2:
                            st.metric("💵 Valor a Entregar", f"R$ {calc["valor_liquido"]:,.2f}")
                            if tipo_cartao == "Débito":
                                st.info("💡 Taxa de 1% sobre o valor do saque")
                            else:
                                st.info("💡 Taxa de 5,33% sobre o valor do saque")
                        
                        st.session_state.simulacao_atual = {
                            "tipo": f"Saque Cartão {tipo_cartao}",
                            "dados": calc,
                            "valor_bruto": valor,
                            "nome": nome or "Não informado",
                            "cpf": cpf or "Não informado",
                            "observacoes": observacoes
                        }
                    except Exception as e:
                        st.error(f"❌ Erro na simulação: {str(e)}")
                
                with col_conf:
                    confirmar = st.form_submit_button("💾 Confirmar e Salvar", use_container_width=True)
                
                if confirmar:
                    try:
                        if "simulacao_atual" not in st.session_state:
                            st.error("❌ Faça a simulação antes de confirmar!")
                        else:
                            sim_data = st.session_state.simulacao_atual
                            
                            # Salvar no Google Sheets
                            worksheet = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", HEADERS)
                            
                            nova_operacao = [
                                obter_data_brasilia(),
                                obter_horario_brasilia(),
                                operador_selecionado,  # Operador responsável
                                sim_data["tipo"],
                                sim_data["nome"],
                                sim_data["cpf"],
                                sim_data["valor_bruto"],
                                sim_data["dados"]["taxa_cliente"],
                                sim_data["dados"]["taxa_banco"],
                                sim_data["dados"]["valor_liquido"],
                                sim_data["dados"]["lucro"],
                                "Concluído",
                                "",
                                f"{(sim_data["dados"]["taxa_cliente"]/sim_data["valor_bruto"])*100:.2f}%",
                                sim_data["observacoes"]
                            ]
                            
                            worksheet.append_row(nova_operacao)
                            st.success(f"✅ {sim_data["tipo"]} de R$ {sim_data["valor_bruto"]:,.2f} registrado com sucesso!")
                            
                            # Limpar simulação
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
                    valor = st.number_input("Valor do Cheque (R$)", min_value=0.01, step=100.0, key="valor_cheque")
                    nome = st.text_input("Nome do Cliente (Opcional)", key="nome_cheque")
                
                with col2:
                    cpf = st.text_input("CPF do Cliente (Opcional)", key="cpf_cheque")
                    observacoes = st.text_area("Observações", key="obs_cheque")
                
                # Campos específicos por tipo de cheque
                dias = 0
                taxa_manual = 0
                data_venc = ""
                
                if tipo_cheque == "Cheque Pré-datado":
                    data_vencimento = st.date_input("Data de Vencimento", min_value=obter_date_brasilia())
                    dias = (data_vencimento - obter_date_brasilia()).days
                    st.info(f"📅 Dias até vencimento: {dias}")
                    data_venc = str(data_vencimento)
                elif tipo_cheque == "Cheque com Taxa Manual":
                    taxa_manual = st.number_input("Taxa Percentual (%)", min_value=0.1, max_value=50.0, step=0.1)
                
                col_sim, col_conf = st.columns([1, 1])
                
                with col_sim:
                    simular = st.form_submit_button("🧮 Simular Operação", use_container_width=True)
                
                if simular and valor > 0:
                    try:
                        if tipo_cheque == "Cheque à Vista":
                            calc = calcular_taxa_cheque_vista(valor)
                            data_venc = obter_data_brasilia()
                        elif tipo_cheque == "Cheque Pré-datado":
                            calc = calcular_taxa_cheque_pre_datado(valor, dias)
                        else:
                            calc = calcular_taxa_cheque_manual(valor, taxa_manual)
                            data_venc = obter_data_brasilia()
                        
                        st.markdown("---")
                        st.markdown(f"### ✅ Simulação - {tipo_cheque}")
                        
                        col_res1, col_res2 = st.columns(2)
                        with col_res1:
                            st.metric("Taxa Percentual", f"{(calc["taxa_cliente"]/valor)*100:.2f}%")
                            st.metric("Taxa em Valores", f"R$ {calc["taxa_cliente"]:,.2f}")
                        
                        with col_res2:
                            st.metric("💵 Valor a Entregar", f"R$ {calc["valor_liquido"]:,.2f}")
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
                            "data_vencimento": data_venc
                        }
                    except Exception as e:
                        st.error(f"❌ Erro na simulação: {str(e)}")
                
                with col_conf:
                    confirmar = st.form_submit_button("💾 Confirmar e Salvar", use_container_width=True)
                
                if confirmar:
                    try:
                        if "simulacao_atual" not in st.session_state:
                            st.error("❌ Faça a simulação antes de confirmar!")
                        else:
                            sim_data = st.session_state.simulacao_atual
                            
                            # Salvar no Google Sheets
                            worksheet = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", HEADERS)
                            
                            nova_operacao = [
                                obter_data_brasilia(),
                                obter_horario_brasilia(),
                                operador_selecionado_cheque,  # Operador responsável
                                sim_data["tipo"],
                                sim_data["nome"],
                                sim_data["cpf"],
                                sim_data["valor_bruto"],
                                sim_data["dados"]["taxa_cliente"],
                                sim_data["dados"]["taxa_banco"],
                                sim_data["dados"]["valor_liquido"],
                                sim_data["dados"]["lucro"],
                                "Concluído",
                                sim_data["data_vencimento"],
                                f"{(sim_data["dados"]["taxa_cliente"]/sim_data["valor_bruto"])*100:.2f}%",
                                sim_data["observacoes"]
                            ]
                            
                            worksheet.append_row(nova_operacao)
                            st.success(f"✅ {sim_data["tipo"]} de R$ {sim_data["valor_bruto"]:,.2f} registrado com sucesso!")
                            
                            # Limpar simulação
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
                
                valor_suprimento = st.number_input("Valor do Suprimento (R$)", min_value=0.01, step=100.0)
                origem_suprimento = st.selectbox("Origem do Suprimento", ["Cofre Principal", "Banco", "Outro"])
                observacoes_sup = st.text_area("Observações do Suprimento")
                
                if st.form_submit_button("💰 Registrar Suprimento", use_container_width=True):
                    try:
                        # Salvar no Google Sheets
                        worksheet = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", HEADERS)
                        
                        nova_operacao = [
                            obter_data_brasilia(),
                            obter_horario_brasilia(),
                            operador_selecionado_suprimento,  # Operador responsável
                            "Suprimento",
                            "Sistema",
                            "N/A",
                            float(valor_suprimento),
                            0,
                            0,
                            float(valor_suprimento),
                            0,
                            "Concluído",
                            "",
                            "0.00%",
                            f"Origem: {origem_suprimento}. {observacoes_sup}"
                        ]
                        
                        worksheet.append_row(nova_operacao)
                        st.success(f"✅ Suprimento de R$ {valor_suprimento:,.2f} registrado com sucesso!")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"❌ Erro ao registrar suprimento: {str(e)}")
        
        with tab4:
            st.markdown("### 📊 Histórico de Operações")
            
            try:
                # Filtros
                col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
                
                with col_filtro1:
                    if st.button("📅 Filtrar por Data"):
                        st.session_state.mostrar_filtro_data = not st.session_state.get("mostrar_filtro_data", False)
                
                if st.session_state.get("mostrar_filtro_data", False):
                    col_data1, col_data2 = st.columns(2)
                    with col_data1:
                        data_inicio = st.date_input("Data Início", value=obter_date_brasilia() - timedelta(days=7))
                    with col_data2:
                        if "data_inicio" in locals():
                            data_fim = st.date_input("Data Fim", value=obter_date_brasilia())
                        else:
                            data_fim = obter_date_brasilia()
                
                with col_filtro2:
                    tipo_operacao_filtro = st.selectbox("Tipo de Operação", ["Todos", "Saque Cartão Débito", "Saque Cartão Crédito", "Troca Cheque à Vista", "Troca Cheque Pré-datado", "Suprimento"])
                
                # Buscar e exibir dados
                operacoes_data = buscar_dados(spreadsheet, "Operacoes_Caixa")
                
                if operacoes_data:
                    # Normalizar dados
                    operacoes_data_normalizada = normalizar_dados_inteligente(operacoes_data)
                    df_operacoes = pd.DataFrame(operacoes_data_normalizada)
                    
                    # Aplicar filtros
                    if tipo_operacao_filtro != "Todos":
                        df_operacoes = df_operacoes[df_operacoes["Tipo_Operacao"] == tipo_operacao_filtro]
                    
                    if st.session_state.get("mostrar_filtro_data", False) and "data_inicio" in locals():
                        try:
                            df_operacoes["Data"] = pd.to_datetime(df_operacoes["Data"], errors="coerce")
                            data_inicio_pd = pd.to_datetime(data_inicio)
                            data_fim_pd = pd.to_datetime(data_fim)
                            df_operacoes = df_operacoes[
                                (df_operacoes["Data"] >= data_inicio_pd) & 
                                (df_operacoes["Data"] <= data_fim_pd)
                            ]
                        except Exception as e:
                            st.warning("⚠️ Erro ao aplicar filtro de data.")
                    
                    # Ordenar por data e hora (mais recente primeiro)
                    if not df_operacoes.empty:
                        try:
                            if "Data" in df_operacoes.columns and "Hora" in df_operacoes.columns:
                                df_operacoes = df_operacoes.sort_values(by=["Data", "Hora"], ascending=False)
                        except Exception as e:
                            st.warning("⚠️ Erro ao ordenar dados.")
                        
                        st.dataframe(df_operacoes, use_container_width=True)
                        
                        # Estatísticas do período
                        st.markdown("---")
                        st.markdown("### 📈 Estatísticas do Período")
                        
                        col_stat1, col_stat2, col_stat3 = st.columns(3)
                        
                        with col_stat1:
                            total_operacoes = len(df_operacoes)
                            st.metric("Total de Operações", total_operacoes)
                        
                        with col_stat2:
                            if "Valor_Bruto" in df_operacoes.columns:
                                total_movimentado = df_operacoes["Valor_Bruto"].sum()
                                st.metric("Total Movimentado", f"R$ {total_movimentado:,.2f}")
                        
                        with col_stat3:
                            if "Taxa_Cliente" in df_operacoes.columns:
                                total_taxas = df_operacoes["Taxa_Cliente"].sum()
                                st.metric("Total em Taxas", f"R$ {total_taxas:,.2f}")
                    else:
                        st.info("Nenhuma operação encontrada com os filtros aplicados.")
                else:
                    st.info("Nenhuma operação registrada ainda.")
            except Exception as e:
                st.error(f"❌ Erro ao carregar histórico: {str(e)}")
    
    except Exception as e:
        st.error(f"❌ Erro ao carregar operações do caixa: {str(e)}")
        st.info("🔄 Tente recarregar a página ou verifique a conexão com o Google Sheets.")


def render_fechamento_diario_simplificado(spreadsheet):
    st.subheader("🗓️ Fechamento Diário do Caixa Interno")

    try:
        # Cabeçalhos para a nova planilha de Fechamento de Caixa
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
            # Alterado para buscar da nova guia de fechamento
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

        st.markdown(f"**Saldo do Caixa no final do dia anterior ({ontem.strftime("%d/%m/%Y")}):** R$ {saldo_dia_anterior:,.2f}")
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
        tipos_troca_cheque = ["Troca Cheque à Vista", "Troca Cheque Pré-datado", "Troca Cheque com Taxa Manual"]
        tipo_suprimento = "Suprimento"

        total_saques_cartao = operacoes_hoje[operacoes_hoje["Tipo_Operacao"].isin(tipos_saque_cartao)]["Valor_Liquido"].sum()
        total_trocas_cheque = operacoes_hoje[operacoes_hoje["Tipo_Operacao"].isin(tipos_troca_cheque)]["Valor_Liquido"].sum()
        total_suprimentos = operacoes_hoje[operacoes_hoje["Tipo_Operacao"] == tipo_suprimento]["Valor_Bruto"].sum()

        saldo_calculado_dia = saldo_dia_anterior + total_suprimentos - (total_saques_cartao + total_trocas_cheque)

        st.markdown("---")
        st.markdown("#### Resumo do Dia")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Saques Cartão", f"R$ {total_saques_cartao:,.2f}")
        with col2:
            st.metric("Total Trocas Cheque", f"R$ {total_trocas_cheque:,.2f}")
        with col3:
            st.metric("Total Suprimentos", f"R$ {total_suprimentos:,.2f}")
        
        st.markdown(f"**Saldo Calculado para Hoje ({hoje.strftime("%d/%m/%Y")}):** R$ {saldo_calculado_dia:,.2f}")
        st.markdown("---")

        # 4. Formulário para registrar o fechamento
        with st.form("form_fechamento_caixa_simplificado", clear_on_submit=True):
            st.markdown("#### Registrar Fechamento Diário")
            dinheiro_contado = st.number_input("Dinheiro Contado na Gaveta (R$)", min_value=0.0, step=10.0, format="%.2f")
            observacoes_fechamento = st.text_area("Observações do Fechamento (Opcional)")

            diferenca = dinheiro_contado - saldo_calculado_dia
            st.markdown(f"**Diferença:** R$ {diferenca:,.2f}")

            if st.form_submit_button("💾 Salvar Fechamento"):
                try:
                    # Simular st.session_state.nome_usuario para teste
                    if 'nome_usuario' not in st.session_state:
                        st.session_state.nome_usuario = "TESTE_USUARIO"

                    # Alterado para usar a nova guia de fechamento
                    fechamento_sheet = get_or_create_worksheet(spreadsheet, "Fechamento_Diario_Caixa_Interno", HEADERS_FECHAMENTO_CAIXA)
                    
                    novo_fechamento = [
                        obter_data_brasilia(),
                        st.session_state.nome_usuario,
                        float(saldo_dia_anterior), # Convertido para float
                        float(total_saques_cartao), # Convertido para float
                        float(total_trocas_cheque), # Convertido para float
                        float(total_suprimentos), # Convertido para float
                        float(saldo_calculado_dia), # Convertido para float
                        float(dinheiro_contado), # Convertido para float
                        float(diferenca), # Convertido para float
                        observacoes_fechamento
                    ]
                    fechamento_sheet.append_row(novo_fechamento)
                    st.success("✅ Fechamento registrado com sucesso!")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"❌ Erro ao salvar fechamento: {e}")

    except Exception as e:
        st.error(f"❌ Erro ao carregar fechamento de caixa: {str(e)}")
        st.info("🔄 Tente recarregar a página ou verifique a conexão com o Google Sheets.")


# Função principal do sistema
def main():
    try:
        if not verificar_login():
            return
        
        # Conectar ao Google Sheets
        spreadsheet = conectar_google_sheets()
        if not spreadsheet:
            st.error("❌ Não foi possível conectar ao Google Sheets. Verifique as credenciais.")
            return
        
        # Interface principal baseada no tipo de usuário
        st.sidebar.title("📋 Menu Principal")
        st.sidebar.success(f"✅ {st.session_state.nome_usuario}")
        st.sidebar.markdown("---")
        
        # Menu baseado no perfil
        if st.session_state.tipo_usuario == "👑 Gerente":
            st.title("👑 Dashboard Gerencial - Sistema Unificado")
            
            opcoes_menu = {
                "📊 Dashboard Caixa": "dashboard_caixa",
                "💳 Operações Caixa": "operacoes_caixa", 
                "🏦 Gestão do Cofre": "cofre",
                "📋 Fechamento Lotérica": "fechamento_loterica",
                "🗓️ Fechamento Diário Caixa Interno": "fechamento_diario_caixa_interno"
            }
            
        elif st.session_state.tipo_usuario == "💳 Operador Caixa":
            st.title("💳 Sistema Caixa Interno")
            
            opcoes_menu = {
                "📊 Dashboard Caixa": "dashboard_caixa",
                "💳 Operações Caixa": "operacoes_caixa",
                "🗓️ Fechamento Diário Caixa Interno": "fechamento_diario_caixa_interno"
            }
            
        else:  # Operador Lotérica
            st.title("🎰 Sistema Lotérica")
            
            opcoes_menu = {
                "📋 Fechamento Lotérica": "fechamento_loterica"
            }
        
        # Navegação
        if "pagina_atual" not in st.session_state:
            st.session_state.pagina_atual = list(opcoes_menu.values())[0]
        
        for nome_opcao, chave_opcao in opcoes_menu.items():
            if st.sidebar.button(nome_opcao, use_container_width=True):
                st.session_state.pagina_atual = chave_opcao
                st.rerun()
        
        st.sidebar.markdown("---")
        if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        # Renderizar página atual
        if st.session_state.pagina_atual == "dashboard_caixa":
            render_dashboard_caixa(spreadsheet)
        elif st.session_state.pagina_atual == "operacoes_caixa":
            render_operacoes_caixa(spreadsheet)
        elif st.session_state.pagina_atual == "cofre":
            render_cofre(spreadsheet)
        elif st.session_state.pagina_atual == "fechamento_loterica":
            render_fechamento_loterica(spreadsheet)
        elif st.session_state.pagina_atual == "fechamento_diario_caixa_interno":
            render_fechamento_diario_simplificado(spreadsheet)
    
    except Exception as e:
        st.error(f"❌ Erro crítico no sistema: {str(e)}")
        st.info("🔄 Recarregue a página para tentar novamente.")
        st.exception(e)

if __name__ == "__main__":
    main()






