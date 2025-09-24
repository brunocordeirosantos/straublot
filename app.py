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
import uuid

#Importar pytz com tratamento de erro
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
            valor_bruto = registro["Valor_Bruto"]
            taxa_cliente = registro["Taxa_Cliente"]
            valor_liquido = registro["Valor_Liquido"]
            
            # Se valor bruto é 0, pular validação
            if valor_bruto == 0:
                dados_corrigidos.append(registro_corrigido)
                continue
            
            # Testar diferentes fatores de correção
            fatores_teste = [1, 0.01, 0.1, 10, 100]
            melhor_fator_taxa = 1
            melhor_fator_liquido = 1
            menor_erro = "Infinity"
            
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
                taxa_banco = registro.get("Taxa_Banco", 0)
                registro_corrigido["Taxa_Banco"] = taxa_banco * melhor_fator_taxa
                
            if "Lucro" in registro and melhor_fator_taxa != 1:
                lucro = registro.get("Lucro", 0)
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
    # Garante que valor está formatado corretamente para Decimal
    valor_dec = Decimal(str(valor).replace(",", "."))
    
    taxa_percentual = Decimal("0.01")
    taxa_cliente = (valor_dec * taxa_percentual).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    taxa_banco = Decimal("1.00")
    lucro = taxa_cliente - taxa_banco
    lucro = max(Decimal("0.00"), lucro)  # Lucro não pode ser negativo
    
    valor_liquido = valor_dec - taxa_cliente

    return {
        "taxa_cliente": taxa_cliente,
        "taxa_banco": taxa_banco,
        "lucro": lucro,
        "valor_liquido": valor_liquido
    }

def calcular_taxa_cartao_credito(valor):
    valor_dec = Decimal(str(valor))
    taxa_cliente = (valor_dec * Decimal("0.0533")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    taxa_banco = (valor_dec * Decimal("0.0433")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    lucro = taxa_cliente - taxa_banco
    valor_liquido = valor_dec - taxa_cliente

    return {
        "taxa_cliente": taxa_cliente,
        "taxa_banco": taxa_banco,
        "lucro": lucro if lucro > Decimal("0") else Decimal("0.00"),
        "valor_liquido": valor_liquido
    }

def calcular_taxa_cheque_vista(valor):
    valor_dec = Decimal(str(valor))
    taxa_cliente = (valor_dec * Decimal("0.02")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    taxa_banco = Decimal("0.00")
    lucro = taxa_cliente
    valor_liquido = valor_dec - taxa_cliente

    return {
        "taxa_cliente": taxa_cliente,
        "taxa_banco": taxa_banco,
        "lucro": lucro,
        "valor_liquido": valor_liquido
    }

def calcular_taxa_cheque_pre_datado(valor, dias):
    valor_dec = Decimal(str(valor))
    taxa_base = valor_dec * Decimal("0.02")  # 2%
    taxa_adicional = valor_dec * Decimal("0.0033") * Decimal(dias)  # 0.33% por dia
    taxa_cliente = (taxa_base + taxa_adicional).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    taxa_banco = Decimal("0.00")
    lucro = taxa_cliente
    valor_liquido = valor_dec - taxa_cliente

    return {
        "taxa_cliente": taxa_cliente,
        "taxa_banco": taxa_banco,
        "lucro": lucro,
        "valor_liquido": valor_liquido
    }

def calcular_taxa_cheque_manual(valor, taxa_percentual):
    valor_dec = Decimal(str(valor))
    taxa_perc_dec = Decimal(str(taxa_percentual)) / Decimal("100")
    taxa_cliente = (valor_dec * taxa_perc_dec).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    taxa_banco = Decimal("0.00")
    lucro = taxa_cliente
    valor_liquido = valor_dec - taxa_cliente

    return {
        "taxa_cliente": taxa_cliente,
        "taxa_banco": taxa_banco,
        "lucro": lucro,
        "valor_liquido": valor_liquido
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


# ------------------------------------------------------------
# Fechamento de Caixa da Lotérica (PDV1/PDV2) — compatível com Suprimento/Sangria do Cofre
def render_fechamento_loterica(spreadsheet):
    import pandas as pd
    import streamlit as st

    st.subheader("📋 Fechamento da Lotérica (PDVs)")

    # ====== Config / cabeçalhos ======
    HEADERS_FECHAMENTO = [
        "Data_Fechamento","PDV","Operador",
        "Qtd_Compra_Bolao","Custo_Unit_Bolao","Total_Compra_Bolao",
        "Qtd_Compra_Raspadinha","Custo_Unit_Raspadinha","Total_Compra_Raspadinha",
        "Qtd_Compra_LoteriaFederal","Custo_Unit_LoteriaFederal","Total_Compra_LoteriaFederal",
        "Qtd_Venda_Bolao","Preco_Unit_Bolao","Total_Venda_Bolao",
        "Qtd_Venda_Raspadinha","Preco_Unit_Raspadinha","Total_Venda_Raspadinha",
        "Qtd_Venda_LoteriaFederal","Preco_Unit_LoteriaFederal","Total_Venda_LoteriaFederal",
        "Movimentacao_Cielo","Pagamento_Premios","Vales_Despesas","Pix_Saida",
        "Retirada_Cofre","Retirada_CaixaInterno","Dinheiro_Gaveta_Final",
        "Saldo_Anterior","Saldo_Final_Calculado","Diferenca_Caixa",
        "Encerrante_Relatorio","Cheques_Recebidos","Suprimento_Cofre","Troco_Anterior","Delta_Encerrante"
    ]
    MOV_PDV_SHEET   = "Movimentacoes_PDV"
    HEADERS_MOV_PDV = ["Data","Hora","PDV","Tipo_Mov","Valor","Vinculo_ID","Operador","Observacoes"]
    COFRE_SHEET     = "Operacoes_Cofre"
    HEADERS_COFRE   = ["Data","Hora","Operador","Tipo","Categoria","Origem","Destino","Valor","Observacoes","Status","Vinculo_ID"]

    PDV_UI_TO_CODE = {
        "Pdv1 - terminal 051650 - bruna": "PDV 1",
        "Pdv2 - terminal 030949 - Karina": "PDV 2",
    }

    # ====== Helpers ======
    K = lambda name: f"fl_{name}"
    def _sheet_for_pdv_code(pdv_code): return "Fechamentos_PDV1" if pdv_code == "PDV 1" else "Fechamentos_PDV2"
    def _to_float(x):
        try: return float(x)
        except: return 0.0

    # ---- Aliases para compatibilidade com dados antigos ----
    SUPR_ALIASES = {"suprimento", "entrada do cofre"}
    SANG_ALIASES = {"sangria", "saida para cofre", "saída para cofre", "retirada para cofre"}
    SANG_INT_ALIASES = {"saída p/ caixa interno","saida p/ caixa interno","retirada p/ caixa interno"}

    def _sum_mov_by_alias(pdv_code, data_alvo, aliases_set):
        total, ids = 0.0, []
        try:
            mov_raw = buscar_dados(spreadsheet, MOV_PDV_SHEET) or []
            df = pd.DataFrame(mov_raw)
            if df.empty: return 0.0, []
            for c in ["Data","PDV","Tipo_Mov","Valor","Vinculo_ID"]:
                if c not in df.columns: df[c] = None
            df["Data"] = pd.to_datetime(df["Data"], errors="coerce").dt.date
            df["Tipo_Mov_norm"] = df["Tipo_Mov"].astype(str).str.lower().str.strip()
            m = (df["Data"].eq(pd.to_datetime(data_alvo).date())
                 & df["PDV"].astype(str).eq(pdv_code)
                 & df["Tipo_Mov_norm"].isin(aliases_set))
            dfx = df.loc[m].copy()
            if dfx.empty: return 0.0, []
            dfx["Valor"] = pd.to_numeric(dfx["Valor"], errors="coerce").fillna(0.0)
            total = float(dfx["Valor"].sum())
            ids = dfx["Vinculo_ID"].dropna().astype(str).tolist()
        except Exception as e:
            st.warning(f"⚠️ Não foi possível ler {MOV_PDV_SHEET}: {e}")
        return total, ids

    def _get_suprimentos_cofre_dia(pdv_code, data_alvo):
        return _sum_mov_by_alias(pdv_code, data_alvo, SUPR_ALIASES)

    def _get_retiradas_cofre_dia(pdv_code, data_alvo):
        return _sum_mov_by_alias(pdv_code, data_alvo, SANG_ALIASES)

    def _get_sangrias_do_dia(pdv_code, data_alvo):
        return _sum_mov_by_alias(pdv_code, data_alvo, SANG_INT_ALIASES)

    def _get_saldo_anterior(pdv_code, data_alvo):
        try:
            ws_name = _sheet_for_pdv_code(pdv_code)
            df = pd.DataFrame(buscar_dados(spreadsheet, ws_name) or [])
            if df.empty or "Data_Fechamento" not in df.columns: return 0.0
            df["Data_Fechamento"] = pd.to_datetime(df["Data_Fechamento"], errors="coerce").dt.date
            df = df[df["PDV"].astype(str).eq(pdv_code)]
            df = df[df["Data_Fechamento"] < pd.to_datetime(data_alvo).date()]
            if df.empty: return 0.0
            if "Saldo_Final_Calculado" in df.columns:
                df["Saldo_Final_Calculado"] = pd.to_numeric(df["Saldo_Final_Calculado"], errors="coerce").fillna(0.0)
                df = df.sort_values("Data_Fechamento")
                return float(df["Saldo_Final_Calculado"].iloc[-1])
            return 0.0
        except Exception:
            return 0.0

    def _get_troco_anterior(pdv_code, data_alvo):
        try:
            ws_name = _sheet_for_pdv_code(pdv_code)
            df = pd.DataFrame(buscar_dados(spreadsheet, ws_name) or [])
            if df.empty or "Data_Fechamento" not in df.columns: return 0.0
            df["Data_Fechamento"] = pd.to_datetime(df["Data_Fechamento"], errors="coerce").dt.date
            df = df[(df["PDV"].astype(str).eq(pdv_code)) & (df["Data_Fechamento"] < pd.to_datetime(data_alvo).date())]
            if df.empty: return 0.0
            df = df.sort_values("Data_Fechamento")
            if "Dinheiro_Gaveta_Final" in df.columns:
                return float(pd.to_numeric(df["Dinheiro_Gaveta_Final"], errors="coerce").fillna(0.0).iloc[-1])
            return 0.0
        except Exception:
            return 0.0

    # ====== RESET SEGURO (flag + rerun) ======
    DEFAULTS = {
        K("supr_manual"): 0.0, K("ret_cofre_manual"): 0.0,
        K("qtd_comp_bolao"): 0, K("custo_unit_bolao"): 0.0,
        K("qtd_venda_bolao"): 0, K("preco_unit_bolao"): 0.0,
        K("qtd_venda_rasp"): 0,  K("preco_unit_rasp"): 0.0,
        K("qtd_venda_fed"): 0,   K("preco_unit_fed"): 0.0,
        K("mov_cielo"): 0.0, K("pag_premios"): 0.0,
        K("vales"): 0.0, K("pix_saida"): 0.0,
        K("cheques"): 0.0, K("encerrante_rel"): 0.0, K("dg_final"): 0.0,
    }

    # Se veio de um salvamento, aplicar defaults ANTES de criar widgets
    if st.session_state.get(K("do_reset"), False):
        for k, v in DEFAULTS.items():
            st.session_state[k] = v
        # manter contexto? (padrão True)
        if not st.session_state.get(K("keep_context"), True):
            st.session_state[K("pdv_ui")] = list(PDV_UI_TO_CODE.keys())[0]
            st.session_state[K("data")] = obter_date_brasilia()
        st.session_state[K("do_reset")] = False  # limpa a flag

    def _reset_fechamento_form(keep_context=True):
        # Em vez de alterar session_state após widgets, só marcamos a flag
        st.session_state[K("keep_context")] = bool(keep_context)
        st.session_state[K("do_reset")] = True
        st.rerun()

    # ---------- UI ----------
    c1, c2 = st.columns(2)
    with c1:
        pdv_ui = st.selectbox("PDV", list(PDV_UI_TO_CODE.keys()), key=K("pdv_ui"))
        pdv_code = PDV_UI_TO_CODE[pdv_ui]
    with c2:
        data_alvo = st.date_input("Data do Fechamento", value=obter_date_brasilia(), key=K("data"))

    operador = st.selectbox(
        "👤 Operador",
        ["", "Bruna","Karina","Edson","Robson","Adiel","Lucas","Ana Paula","Fernanda","CRIS"],
        key=K("operador")
    )

    # 👉 Movimentos com Cofre
    st.markdown("### Movimentos com Cofre")
    supr_manual = st.number_input(
        "Suprimento do Cofre → entra no PDV (lançar agora)",
        min_value=0.0, step=50.0, format="%.2f",
        key=K("supr_manual"),
        help="Cria Suprimento no PDV e Saída no Cofre."
    )
    ret_cofre_manual = st.number_input(
        "Retirada para Cofre ← sai do PDV (lançar agora)",
        min_value=0.0, step=50.0, format="%.2f",
        key=K("ret_cofre_manual"),
        help="Cria Sangria no PDV e Entrada no Cofre."
    )
    st.markdown("---")

    # Compras / Vendas
    st.markdown("### Compras (estoque)")
    cc1, cc2, cc3 = st.columns(3)
    with cc1:
        qtd_comp_bolao = st.number_input("Qtd Compra Bolão (un)", min_value=0, step=1, format="%d", key=K("qtd_comp_bolao"))
    with cc2:
        custo_unit_bolao = st.number_input("Custo Unit Bolão (R$)", min_value=0.0, step=5.0, format="%.2f", key=K("custo_unit_bolao"))
    with cc3:
        total_comp_bolao = qtd_comp_bolao * custo_unit_bolao
        st.metric("Total Compra Bolão", f"R$ {total_comp_bolao:,.2f}")

    st.info("🛈 Compras de **Raspadinha** e **Loteria Federal** são lançadas na **Gestão da Lotérica**.")

    st.markdown("---")
    st.markdown("### Vendas")
    vb1, vb2, vb3 = st.columns(3)
    with vb1:
        qtd_venda_bolao = st.number_input("Qtd Venda Bolão (un)", min_value=0, step=1, format="%d", key=K("qtd_venda_bolao"))
    with vb2:
        preco_unit_bolao = st.number_input("Preço Unit Bolão (R$)", min_value=0.0, step=5.0, format="%.2f", key=K("preco_unit_bolao"))
    with vb3:
        total_venda_bolao = qtd_venda_bolao * preco_unit_bolao
        st.metric("Total Venda Bolão", f"R$ {total_venda_bolao:,.2f}")

    vr1, vr2, vr3 = st.columns(3)
    with vr1:
        qtd_venda_rasp = st.number_input("Qtd Venda Raspadinha (un)", min_value=0, step=1, format="%d", key=K("qtd_venda_rasp"))
    with vr2:
        preco_unit_rasp = st.number_input("Preço Unit Raspadinha (R$)", min_value=0.0, step=1.0, format="%.2f", key=K("preco_unit_rasp"))
    with vr3:
        total_venda_rasp = qtd_venda_rasp * preco_unit_rasp
        st.metric("Total Venda Raspadinha", f"R$ {total_venda_rasp:,.2f}")

    vf1, vf2, vf3 = st.columns(3)
    with vf1:
        qtd_venda_fed = st.number_input("Qtd Venda Loteria Federal (un)", min_value=0, step=1, format="%d", key=K("qtd_venda_fed"))
    with vf2:
        preco_unit_fed = st.number_input("Preço Unit Loteria Federal (R$)", min_value=0.0, step=1.0, format="%.2f", key=K("preco_unit_fed"))
    with vf3:
        total_venda_fed = qtd_venda_fed * preco_unit_fed
        st.metric("Total Venda Loteria Federal", f"R$ {total_venda_fed:,.2f}")

    total_vendas = total_venda_bolao + total_venda_rasp + total_venda_fed

    st.markdown("---")
    st.markdown("### Outras movimentações do dia")
    om1, om2, om3 = st.columns(3)
    with om1:
        movimentacao_cielo = st.number_input("Movimentação Cielo (R$)", min_value=0.0, step=50.0, format="%.2f", key=K("mov_cielo"))
    with om2:
        pagamento_premios = st.number_input("Pagamento de Prêmios (R$)", min_value=0.0, step=50.0, format="%.2f", key=K("pag_premios"))
    with om3:
        vales_despesas = st.number_input("Vales/Despesas (R$)", min_value=0.0, step=50.0, format="%.2f", key=K("vales"))

    om4, om5 = st.columns(2)
    with om4:
        pix_saida = st.number_input("PIX Saída (R$)", min_value=0.0, step=50.0, format="%.2f", key=K("pix_saida"))
    with om5:
        cheques_recebidos = st.number_input("Cheques Recebidos (R$)", min_value=0.0, step=50.0, format="%.2f", key=K("cheques"))

    # ===== Auto (busca em Movimentacoes_PDV) =====
    total_sangrias_pdv, _ = _get_sangrias_do_dia(pdv_code, data_alvo)
    st.text_input("Retirada p/ Caixa Interno (auto)", value=f"R$ {total_sangrias_pdv:,.2f}", disabled=True)

    supr_cofre_auto, _ = _get_suprimentos_cofre_dia(pdv_code, data_alvo)
    st.text_input("Suprimento do Cofre (auto)", value=f"R$ {supr_cofre_auto:,.2f}", disabled=True)

    ret_cofre_auto, _ = _get_retiradas_cofre_dia(pdv_code, data_alvo)
    st.text_input("Retirada para Cofre (auto)", value=f"R$ {ret_cofre_auto:,.2f}", disabled=True)

    st.markdown("---")
    st.markdown("### Fechamento de caixa")
    saldo_anterior = _get_saldo_anterior(pdv_code, data_alvo)
    troco_anterior = _get_troco_anterior(pdv_code, data_alvo)
    encerrante_rel = st.number_input("Encerrante do Relatório (pode ser negativo)", step=50.0, format="%.2f", key=K("encerrante_rel"))
    dg_final       = st.number_input("Dinheiro em Gaveta (final do dia) (R$)", min_value=0.0, step=50.0, format="%.2f", key=K("dg_final"))

    supr_total       = _to_float(supr_cofre_auto) + _to_float(supr_manual)
    retirada_cofre_t = _to_float(ret_cofre_auto) + _to_float(ret_cofre_manual)

    saldo_final_calc = (
        _to_float(saldo_anterior)
        + (_to_float(total_vendas) - _to_float(movimentacao_cielo))
        - _to_float(pagamento_premios)
        - _to_float(vales_despesas)
        - _to_float(pix_saida)
        - _to_float(total_sangrias_pdv)
        - _to_float(retirada_cofre_t)
    )
    diferenca = _to_float(dg_final) - _to_float(saldo_final_calc)

    # Conferência
    st.markdown("#### 📑 Conferência rápida (dia)")
    entradas = pd.DataFrame([
        ["Encerrante do Relatório",             _to_float(encerrante_rel)],
        ["Troco do dia anterior (auto)",        _to_float(troco_anterior)],
        ["Suprimento do Cofre (auto + manual)", _to_float(supr_total)],
        ["Vendas — Bolão",                      _to_float(total_venda_bolao)],
        ["Vendas — Raspadinha",                 _to_float(total_venda_rasp)],
        ["Vendas — Loteria Federal",            _to_float(total_venda_fed)],
    ], columns=["Categoria","Valor_R$"])
    saidas = pd.DataFrame([
        ["Movimentação Cielo",                  _to_float(movimentacao_cielo)],
        ["PIX Saída",                            _to_float(pix_saida)],
        ["Cheques Recebidos",                    _to_float(cheques_recebidos)],
        ["Pagamento de Prêmios",                 _to_float(pagamento_premios)],
        ["Vales/Despesas",                       _to_float(vales_despesas)],
        ["Compra — Bolão",                       _to_float(total_comp_bolao)],
        ["Retirada p/ Caixa Interno (auto)",     _to_float(total_sangrias_pdv)],
        ["Retirada para Cofre (auto + manual)",  _to_float(retirada_cofre_t)],
        ["Dinheiro em Gaveta (final)",           _to_float(dg_final)],
    ], columns=["Categoria","Valor_R$"])
    entradas_tot = float(entradas["Valor_R$"].sum())
    saidas_tot   = float(saidas["Valor_R$"].sum())
    delta_enc_calc = entradas_tot - saidas_tot

    ctbl1, ctbl2 = st.columns(2)
    with ctbl1:
        st.dataframe(pd.concat([entradas, pd.DataFrame([{"Categoria":"TOTAL","Valor_R$":entradas_tot}])], ignore_index=True),
                     use_container_width=True)
    with ctbl2:
        st.dataframe(pd.concat([saidas,   pd.DataFrame([{"Categoria":"TOTAL","Valor_R$":saidas_tot}])],   ignore_index=True),
                     use_container_width=True)
    st.caption(f"Δ Encerrante (Entradas − Saídas): **R$ {delta_enc_calc:,.2f}** — ideal é 0,00.")

    st.markdown("#### 🎯 Indicadores finais")
    k1, k2 = st.columns(2)
    with k1: st.metric("Saldo calculado (Encerrante)", f"R$ {delta_enc_calc:,.2f}")
    with k2: st.metric("Troco do dia anterior (auto)", f"R$ {troco_anterior:,.2f}")

    # ---------- Salvar ----------
    if st.button("💾 Salvar Fechamento", use_container_width=True):
        try:
            ws_name = _sheet_for_pdv_code(pdv_code)
            ws = get_or_create_worksheet(spreadsheet, ws_name, HEADERS_FECHAMENTO)

            # duplicidade PDV+Data
            df_exist = pd.DataFrame(buscar_dados(spreadsheet, ws_name) or [])
            existe_registro = False
            if not df_exist.empty and {"Data_Fechamento","PDV"}.issubset(df_exist.columns):
                df_exist["Data_Fechamento"] = pd.to_datetime(df_exist["Data_Fechamento"], errors="coerce").dt.date
                mask_dup = (df_exist["PDV"].astype(str).eq(pdv_code) &
                            df_exist["Data_Fechamento"].eq(pd.to_datetime(data_alvo).date()))
                existe_registro = bool(df_exist.loc[mask_dup].shape[0] > 0)
            if existe_registro:
                st.error("❌ Já existe um fechamento para este PDV nesta data. Edite/remova o registro existente.")
                st.stop()

            # 1) Suprimento manual => Mov_PDV: Suprimento | Cofre: Saída
            if _to_float(supr_manual) > 0:
                ws_mov_pdv = get_or_create_worksheet(spreadsheet, MOV_PDV_SHEET, HEADERS_MOV_PDV)
                ws_cofre   = get_or_create_worksheet(spreadsheet, COFRE_SHEET, HEADERS_COFRE)
                hora = obter_horario_brasilia()
                vinc = f"SUPR|{str(data_alvo)}|{pdv_code}|{_to_float(supr_manual):.2f}|{hora}"
                mov_exist = pd.DataFrame(buscar_dados(spreadsheet, MOV_PDV_SHEET) or [])
                if not (("Vinculo_ID" in mov_exist.columns) and mov_exist["Vinculo_ID"].astype(str).eq(vinc).any()):
                    ws_mov_pdv.append_row([str(data_alvo), hora, pdv_code, "Suprimento",
                                           float(_to_float(supr_manual)), vinc, st.session_state.get("nome_usuario",""),
                                           "lançado no Fechamento PDV"])
                    ws_cofre.append_row([str(obter_data_brasilia()), hora, st.session_state.get("nome_usuario",""),
                                         "Saída","Transferência para Caixa Lotérica","Cofre Principal",
                                         f"Caixa Lotérica - {pdv_code}", float(_to_float(supr_manual)),
                                         "lançado via Fechamento PDV","Concluído", vinc])

            # 2) Retirada p/ Cofre manual => Mov_PDV: Sangria | Cofre: Entrada
            if _to_float(ret_cofre_manual) > 0:
                ws_mov_pdv = get_or_create_worksheet(spreadsheet, MOV_PDV_SHEET, HEADERS_MOV_PDV)
                ws_cofre   = get_or_create_worksheet(spreadsheet, COFRE_SHEET, HEADERS_COFRE)
                hora = obter_horario_brasilia()
                vinc = f"RETCOFRE|{str(data_alvo)}|{pdv_code}|{_to_float(ret_cofre_manual):.2f}|{hora}"
                mov_exist = pd.DataFrame(buscar_dados(spreadsheet, MOV_PDV_SHEET) or [])
                if not (("Vinculo_ID" in mov_exist.columns) and mov_exist["Vinculo_ID"].astype(str).eq(vinc).any()):
                    ws_mov_pdv.append_row([str(data_alvo), hora, pdv_code, "Sangria",
                                           float(_to_float(ret_cofre_manual)), vinc, st.session_state.get("nome_usuario",""),
                                           "lançado no Fechamento PDV"])
                    ws_cofre.append_row([str(obter_data_brasilia()), hora, st.session_state.get("nome_usuario",""),
                                         "Entrada","Transferência do Caixa Lotérica",f"Caixa Lotérica - {pdv_code}",
                                         "Cofre Principal", float(_to_float(ret_cofre_manual)),
                                         "lançado via Fechamento PDV","Concluído", vinc])

            # 3) Salvar o fechamento
            row = [
                str(data_alvo), pdv_code, st.session_state.get(K("operador"), ""),
                int(qtd_comp_bolao), float(custo_unit_bolao), float(total_comp_bolao),
                0, 0.0, 0.0,
                0, 0.0, 0.0,
                int(qtd_venda_bolao), float(preco_unit_bolao), float(total_venda_bolao),
                int(qtd_venda_rasp),  float(preco_unit_rasp),  float(total_venda_rasp),
                int(qtd_venda_fed),   float(preco_unit_fed),   float(total_venda_fed),
                float(movimentacao_cielo), float(pagamento_premios), float(vales_despesas), float(pix_saida),
                float(retirada_cofre_t), float(total_sangrias_pdv), float(dg_final),
                float(saldo_anterior), float(saldo_final_calc), float(diferenca),
                float(encerrante_rel), float(cheques_recebidos), float(supr_total), float(troco_anterior),
                float(delta_enc_calc)
            ]
            ws.append_row(row)

            st.success("✅ Fechamento salvo com sucesso!")
            st.cache_data.clear()

            # Reset seguro (sem tocar no session_state após widgets)
            _reset_fechamento_form(keep_context=True)

        except Exception as e:
            st.error(f"❌ Erro ao salvar fechamento: {e}")





# ------------------------------------------------------------
# 📈 Gestão Lotérica — Estoque + Relatórios + Sincronização + Edição/Remoção
# ------------------------------------------------------------
def render_gestao_loterica(spreadsheet):
    import pandas as pd
    import numpy as np
    from datetime import timedelta

    st.subheader("📈 Gestão Lotérica — Estoque & Relatórios")

    # Planilhas utilizadas
    SHEET_MOV = "Estoque_Loterica_Mov"
    FECH_PDV = {"PDV 1": "Fechamentos_PDV1", "PDV 2": "Fechamentos_PDV2"}
    PRODUTOS = ["Bolão", "Raspadinha", "Loteria Federal"]

    # Cabeçalho dos fechamentos (com novos campos ao fim)
    HEADERS_FECHAMENTO = [
        "Data_Fechamento", "PDV", "Operador",
        "Qtd_Compra_Bolao", "Custo_Unit_Bolao", "Total_Compra_Bolao",
        "Qtd_Compra_Raspadinha", "Custo_Unit_Raspadinha", "Total_Compra_Raspadinha",
        "Qtd_Compra_LoteriaFederal", "Custo_Unit_LoteriaFederal", "Total_Compra_LoteriaFederal",
        "Qtd_Venda_Bolao", "Preco_Unit_Bolao", "Total_Venda_Bolao",
        "Qtd_Venda_Raspadinha", "Preco_Unit_Raspadinha", "Total_Venda_Raspadinha",
        "Qtd_Venda_LoteriaFederal", "Preco_Unit_LoteriaFederal", "Total_Venda_LoteriaFederal",
        "Movimentacao_Cielo", "Pagamento_Premios", "Vales_Despesas", "Pix_Saida",
        "Retirada_Cofre", "Retirada_CaixaInterno", "Dinheiro_Gaveta_Final",
        "Saldo_Anterior", "Saldo_Final_Calculado", "Diferenca_Caixa",
        "Encerrante_Relatorio", "Cheques_Recebidos", "Suprimento_Cofre", "Troco_Anterior", "Delta_Encerrante"
    ]

    # Movimentos de estoque
    HEADERS_MOV = [
        "Data", "Hora", "PDV", "Produto", "Tipo_Mov",  # Entrada | Venda | Ajuste+ | Ajuste-
        "Qtd", "Valor_Unit", "Valor_Total", "Obs",
        "Origem", "Chave_Sync"
    ]

    # garante existência da planilha de movimentos
    try:
        get_or_create_worksheet(spreadsheet, SHEET_MOV, HEADERS_MOV)
    except Exception as e:
        st.error(f"❌ Não foi possível garantir a planilha de movimentos: {e}")
        return

    # -------------------- utils internos --------------------
    def _load_mov():
        dados = buscar_dados(spreadsheet, SHEET_MOV) or []
        df = pd.DataFrame(dados)
        if df.empty:
            df = pd.DataFrame(columns=HEADERS_MOV)
        for c in ["Qtd", "Valor_Unit", "Valor_Total"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
        return df

    def _saldo_estoque(df_mov):
        if df_mov.empty:
            return pd.DataFrame(columns=["PDV", "Produto", "Saldo_Qtd", "Custo_Médio", "Valor_Custo_Estimado"])
        df = df_mov.copy()
        df["fator"] = 0
        df.loc[df["Tipo_Mov"].isin(["Entrada", "Ajuste+"]), "fator"] = 1
        df.loc[df["Tipo_Mov"].isin(["Venda", "Ajuste-"]), "fator"] = -1
        df["Mov_Qtd"] = df["Qtd"] * df["fator"]
        df_ent = df[df["fator"] == 1].groupby(["PDV", "Produto"], as_index=False)[["Qtd", "Valor_Total"]].sum()
        if not df_ent.empty:
            df_ent["Custo_Médio"] = (df_ent["Valor_Total"] / df_ent["Qtd"]).replace([np.inf, -np.inf], 0).fillna(0)
        else:
            df_ent = pd.DataFrame(columns=["PDV", "Produto", "Qtd", "Valor_Total", "Custo_Médio"])
        df_saldo = df.groupby(["PDV", "Produto"], as_index=False)["Mov_Qtd"].sum().rename(columns={"Mov_Qtd": "Saldo_Qtd"})
        df_saldo = df_saldo.merge(df_ent[["PDV", "Produto", "Custo_Médio"]], on=["PDV", "Produto"], how="left").fillna({"Custo_Médio": 0})
        df_saldo["Valor_Custo_Estimado"] = df_saldo["Saldo_Qtd"] * df_saldo["Custo_Médio"]
        return df_saldo

    def _sheet_for_pdv(pdv): 
        return FECH_PDV[pdv]

    def _to_float(x):
        try:
            return float(x)
        except Exception:
            return 0.0

    def _get_sangrias_do_dia(pdv, data_alvo):
        """Saídas p/ Caixa Interno do dia (auto)."""
        total, ids = 0.0, []
        try:
            mov_raw = buscar_dados(spreadsheet, "Movimentacoes_PDV") or []
            df = pd.DataFrame(mov_raw)
            if not df.empty:
                for col in ["Data","PDV","Tipo_Mov","Valor","Vinculo_ID"]:
                    if col not in df.columns: 
                        df[col] = None
                df["Data"] = pd.to_datetime(df["Data"], errors="coerce").dt.date
                m = (df["Data"].eq(pd.to_datetime(data_alvo).date())
                     & df["PDV"].astype(str).eq(pdv)
                     & df["Tipo_Mov"].astype(str).eq("Saída p/ Caixa Interno"))
                dfd = df.loc[m].copy()
                if not dfd.empty:
                    dfd["Valor"] = pd.to_numeric(dfd["Valor"], errors="coerce").fillna(0.0)
                    total = float(dfd["Valor"].sum())
                    ids = dfd["Vinculo_ID"].dropna().astype(str).tolist()
        except Exception as e:
            st.warning(f"⚠️ Não foi possível ler Movimentacoes_PDV (sangrias): {e}")
        return total, ids

    def _get_suprimentos_cofre_do_dia(pdv, data_alvo):
        """
        Entradas vindas do Cofre no dia (auto).
        Aceita 'Entrada do Cofre' e 'Suprimento do Cofre' como Tipo_Mov.
        """
        total, ids = 0.0, []
        try:
            mov_raw = buscar_dados(spreadsheet, "Movimentacoes_PDV") or []
            df = pd.DataFrame(mov_raw)
            if not df.empty:
                for col in ["Data","PDV","Tipo_Mov","Valor","Vinculo_ID"]:
                    if col not in df.columns: 
                        df[col] = None
                df["Data"] = pd.to_datetime(df["Data"], errors="coerce").dt.date
                m = (df["Data"].eq(pd.to_datetime(data_alvo).date())
                     & df["PDV"].astype(str).eq(pdv)
                     & df["Tipo_Mov"].astype(str).isin(["Entrada do Cofre", "Suprimento do Cofre"]))
                dfe = df.loc[m].copy()
                if not dfe.empty:
                    dfe["Valor"] = pd.to_numeric(dfe["Valor"], errors="coerce").fillna(0.0)
                    total = float(dfe["Valor"].sum())
                    ids = dfe["Vinculo_ID"].dropna().astype(str).tolist()
        except Exception as e:
            st.warning(f"⚠️ Não foi possível ler Movimentacoes_PDV (entradas do cofre): {e}")
        return total, ids

    def _get_saldo_anterior(pdv, data_alvo):
        """Último Saldo_Final_Calculado anterior (para manter compatibilidade)."""
        try:
            ws_name = _sheet_for_pdv(pdv)
            df = pd.DataFrame(buscar_dados(spreadsheet, ws_name) or [])
            if df.empty or "Data_Fechamento" not in df.columns: 
                return 0.0
            df["Data_Fechamento"] = pd.to_datetime(df["Data_Fechamento"], errors="coerce").dt.date
            df = df[(df["PDV"].astype(str).eq(pdv)) & (df["Data_Fechamento"] < pd.to_datetime(data_alvo).date())]
            if df.empty: 
                return 0.0
            df = df.sort_values("Data_Fechamento")
            if "Saldo_Final_Calculado" in df.columns:
                return float(pd.to_numeric(df["Saldo_Final_Calculado"], errors="coerce").fillna(0.0).iloc[-1])
            return 0.0
        except Exception:
            return 0.0

    def _get_troco_anterior(pdv, data_alvo):
        """Dinheiro em Gaveta do dia anterior (troco) — usado no Lado Esquerdo."""
        try:
            ws_name = _sheet_for_pdv(pdv)
            df = pd.DataFrame(buscar_dados(spreadsheet, ws_name) or [])
            if df.empty or "Data_Fechamento" not in df.columns: 
                return 0.0
            df["Data_Fechamento"] = pd.to_datetime(df["Data_Fechamento"], errors="coerce").dt.date
            df = df[(df["PDV"].astype(str).eq(pdv)) & (df["Data_Fechamento"] < pd.to_datetime(data_alvo).date())]
            if df.empty: 
                return 0.0
            df = df.sort_values("Data_Fechamento")
            if "Dinheiro_Gaveta_Final" in df.columns:
                return float(pd.to_numeric(df["Dinheiro_Gaveta_Final"], errors="coerce").fillna(0.0).iloc[-1])
            return 0.0
        except Exception:
            return 0.0

    def _find_row_by_pdv_date(ws, target_pdv, target_date):
        try:
            vals = ws.get_all_values()
            if not vals: 
                return None
            headers = vals[0]
            try:
                i_pdv = headers.index("PDV"); i_dt = headers.index("Data_Fechamento")
            except ValueError:
                return None
            tgt_date = pd.to_datetime(target_date, errors="coerce").date()
            for i in range(1, len(vals)):
                row = vals[i]
                if len(row) <= max(i_pdv, i_dt): 
                    continue
                r_pdv = str(row[i_pdv]); r_dt = pd.to_datetime(row[i_dt], errors="coerce")
                if pd.isna(r_dt): 
                    continue
                if (r_pdv == target_pdv) and (r_dt.date() == tgt_date):
                    return i + 1
            return None
        except Exception:
            return None

    # -------- helpers de normalização e conciliação --------
    _num_cols_all = [
        "Qtd_Compra_Bolao","Custo_Unit_Bolao","Total_Compra_Bolao",
        "Qtd_Compra_Raspadinha","Custo_Unit_Raspadinha","Total_Compra_Raspadinha",
        "Qtd_Compra_LoteriaFederal","Custo_Unit_LoteriaFederal","Total_Compra_LoteriaFederal",
        "Qtd_Venda_Bolao","Preco_Unit_Bolao","Total_Venda_Bolao",
        "Qtd_Venda_Raspadinha","Preco_Unit_Raspadinha","Total_Venda_Raspadinha",
        "Qtd_Venda_LoteriaFederal","Preco_Unit_LoteriaFederal","Total_Venda_LoteriaFederal",
        "Movimentacao_Cielo","Pagamento_Premios","Vales_Despesas","Pix_Saida",
        "Retirada_Cofre","Retirada_CaixaInterno","Dinheiro_Gaveta_Final",
        "Saldo_Anterior","Saldo_Final_Calculado","Diferenca_Caixa",
        "Encerrante_Relatorio","Cheques_Recebidos","Suprimento_Cofre","Troco_Anterior","Delta_Encerrante"
    ]

    def _normalize_fech(df):
        """Garante colunas, tipagem e calcula Lado Esquerdo/Direito do Encerrante."""
        if df.empty:
            return pd.DataFrame(columns=HEADERS_FECHAMENTO + ["Left_Enc","Right_Enc","Delta_Enc_Calc","Total_Vendas_Soma"])
        # garante colunas
        for c in HEADERS_FECHAMENTO:
            if c not in df.columns: 
                df[c] = 0
        # tipa
        for c in _num_cols_all:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
        # soma vendas
        df["Total_Vendas_Soma"] = df["Total_Venda_Bolao"] + df["Total_Venda_Raspadinha"] + df["Total_Venda_LoteriaFederal"]
        # fórmula de conciliação do Encerrante (regra acordada)
        df["Left_Enc"]  = df["Encerrante_Relatorio"] + df["Troco_Anterior"] + df["Suprimento_Cofre"] + df["Total_Vendas_Soma"]
        df["Right_Enc"] = df["Movimentacao_Cielo"] + df["Pix_Saida"] + df["Cheques_Recebidos"] \
                          + df["Pagamento_Premios"] + df["Vales_Despesas"] + df["Retirada_Cofre"] \
                          + df["Total_Compra_Bolao"] + df["Retirada_CaixaInterno"] + df["Dinheiro_Gaveta_Final"]
        df["Delta_Enc_Calc"] = df["Left_Enc"] - df["Right_Enc"]
        return df

    # ---------------------- abas ----------------------
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📦 Estoque", "📊 Relatórios", "🧾 Conferência de Fechamentos", "🔄 Sincronização", "✏️ Editar/Remover"
    ])

    # ---------------------- TAB 1 — ESTOQUE ----------------------
    with tab1:
        st.markdown("#### 📦 Estoque Atual por PDV/Produto")

        df_mov = _load_mov()
        c1, c2 = st.columns(2)
        with c1:
            filtro_pdv = st.selectbox("Filtrar por PDV", ["Todos"] + list(FECH_PDV.keys()), key="flt_pdv_est")
        with c2:
            filtro_prod = st.selectbox("Filtrar por Produto", ["Todos"] + PRODUTOS, key="flt_prod_est")

        df_fil = df_mov.copy()
        if filtro_pdv != "Todos": 
            df_fil = df_fil[df_fil["PDV"] == filtro_pdv]
        if filtro_prod != "Todos": 
            df_fil = df_fil[df_fil["Produto"] == filtro_prod]

        df_saldo = _saldo_estoque(df_fil)
        if df_saldo.empty:
            st.info("Nenhum movimento de estoque lançado ainda.")
        else:
            colA, colB, colC = st.columns(3)
            with colA: st.metric("Itens (linhas) no estoque", len(df_saldo))
            with colB: st.metric("Soma de quantidades", f"{df_saldo['Saldo_Qtd'].sum():,.0f}")
            with colC: st.metric("Valor de custo estimado", f"R$ {df_saldo['Valor_Custo_Estimado'].sum():,.2f}")
            st.dataframe(df_saldo.sort_values(["PDV","Produto"]), use_container_width=True)
            st.download_button("⬇️ Baixar estoque (CSV)",
                               data=df_saldo.to_csv(index=False).encode("utf-8"),
                               file_name="estoque_pdv_produto.csv", mime="text/csv")

        st.markdown("---")
        st.markdown("#### ✍️ Ajuste Manual de Estoque")
        with st.form("form_ajuste_estoque", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1: aj_pdv = st.selectbox("PDV", list(FECH_PDV.keys()), key="aj_pdv")
            with c2: aj_prod = st.selectbox("Produto", PRODUTOS, key="aj_prod")
            with c3: aj_tipo = st.selectbox("Tipo de Ajuste", ["Ajuste+", "Ajuste-"], key="aj_tipo")
            c4, c5 = st.columns(2)
            with c4: aj_qtd = st.number_input("Quantidade", min_value=0.0, step=1.0, format="%.0f", key="aj_qtd")
            with c5: aj_val = st.number_input("Valor Unitário (R$) (apenas p/ Ajuste+)", min_value=0.0, step=0.01, format="%.2f", key="aj_vu")
            aj_obs = st.text_input("Observações (opcional)", key="aj_obs")
            btn_aj = st.form_submit_button("💾 Registrar Ajuste", use_container_width=True)
        if btn_aj:
            try:
                if aj_qtd <= 0: 
                    st.error("Informe quantidade > 0."); 
                    st.stop()
                ws = get_or_create_worksheet(spreadsheet, SHEET_MOV, HEADERS_MOV)
                now_d, now_h = obter_data_brasilia(), obter_horario_brasilia()
                valor_total = float(aj_qtd) * float(aj_val) if aj_tipo == "Ajuste+" else 0.0
                ws.append_row([now_d, now_h, aj_pdv, aj_prod, aj_tipo,
                               float(aj_qtd), float(aj_val), float(valor_total),
                               aj_obs, "AJUSTE_MANUAL", ""])
                st.success("✅ Ajuste registrado.")
                st.cache_data.clear(); st.experimental_rerun()
            except Exception as e:
                st.error(f"❌ Erro ao registrar ajuste: {e}")

    # -------------------- TAB 2 — RELATÓRIOS ---------------------
    with tab2:
        st.markdown("#### 📊 Relatórios e Conciliação do Encerrante")
        c1, c2, c3 = st.columns(3)
        with c1: pdv_r = st.selectbox("PDV", ["Todos"] + list(FECH_PDV.keys()), key="rel_pdv")
        with c2: ini = st.date_input("Início", value=obter_date_brasilia() - timedelta(days=7), key="rel_ini")
        with c3: fim = st.date_input("Fim", value=obter_date_brasilia(), key="rel_fim")

        frames = []
        for pdv, sheet in FECH_PDV.items():
            try:
                dados = buscar_dados(spreadsheet, sheet) or []
                df = pd.DataFrame(dados)
                if df.empty: 
                    continue
                df["Data_Fechamento"] = pd.to_datetime(df["Data_Fechamento"], errors="coerce").dt.date
                df = df[(df["Data_Fechamento"] >= ini) & (df["Data_Fechamento"] <= fim)]
                if df.empty: 
                    continue
                df["PDV"] = pdv
                frames.append(df)
            except Exception as e:
                st.warning(f"⚠️ Erro ao buscar {sheet}: {e}")

        if not frames:
            st.info("Sem dados no período selecionado.")
        else:
            df_all = _normalize_fech(pd.concat(frames, ignore_index=True))
            if pdv_r != "Todos": 
                df_all = df_all[df_all["PDV"] == pdv_r]

            # KPIs compras x vendas
            total_compra = df_all[["Total_Compra_Bolao","Total_Compra_Raspadinha","Total_Compra_LoteriaFederal"]].sum().sum()
            total_venda  = df_all[["Total_Venda_Bolao","Total_Venda_Raspadinha","Total_Venda_LoteriaFederal"]].sum().sum()
            margem_bruta = total_venda - total_compra

            k1, k2, k3 = st.columns(3)
            with k1: st.metric("Total Compras", f"R$ {total_compra:,.2f}")
            with k2: st.metric("Total Vendas", f"R$ {total_venda:,.2f}")
            with k3: st.metric("Margem Bruta", f"R$ {margem_bruta:,.2f}",
                            f"{(margem_bruta/total_venda*100 if total_venda>0 else 0):.1f}%")

            # Conciliação do Encerrante — período (mesma fórmula do fechamento)
            left_period  = float(df_all["Left_Enc"].sum())
            right_period = float(df_all["Right_Enc"].sum())
            delta_period = left_period - right_period
            cA, cB, cC = st.columns(3)
            with cA: st.metric("Lado Esquerdo (período)", f"R$ {left_period:,.2f}")
            with cB: st.metric("Lado Direito (período)", f"R$ {right_period:,.2f}")
            with cC: st.metric("Δ Encerrante (período)", f"R$ {delta_period:,.2f}")

            # ======= NOVO: tabelas por lado (Entradas x Saídas) =======
            # ENTRADAS (Lado Esquerdo)
            entradas_dict = {
                "Encerrante do Relatório": float(df_all["Encerrante_Relatorio"].sum()),
                "Troco do dia anterior":   float(df_all["Troco_Anterior"].sum()),
                "Suprimentos do Cofre":    float(df_all["Suprimento_Cofre"].sum()),
                "Vendas Bolão":            float(df_all["Total_Venda_Bolao"].sum()),
                "Vendas Raspadinha":       float(df_all["Total_Venda_Raspadinha"].sum()),
                "Vendas Loteria Federal":  float(df_all["Total_Venda_LoteriaFederal"].sum()),
            }
            df_entradas = pd.DataFrame(
                [{"Categoria": k, "Total_R$": v} for k, v in entradas_dict.items()]
            ).sort_values("Total_R$", ascending=False)

            # SAÍDAS (Lado Direito)
            saidas_dict = {
                "Movimentação Cielo":      float(df_all["Movimentacao_Cielo"].sum()),
                "PIX Saída":               float(df_all["Pix_Saida"].sum()),
                "Cheques Recebidos":       float(df_all["Cheques_Recebidos"].sum()),
                "Pagamento de Prêmios":    float(df_all["Pagamento_Premios"].sum()),
                "Vales/Despesas":          float(df_all["Vales_Despesas"].sum()),
                "Retirada para Cofre":     float(df_all["Retirada_Cofre"].sum()),
                "Total Compra Bolão":      float(df_all["Total_Compra_Bolao"].sum()),
                "Retirada p/ Caixa Interno": float(df_all["Retirada_CaixaInterno"].sum()),
                "Dinheiro em Gaveta":      float(df_all["Dinheiro_Gaveta_Final"].sum()),
            }
            df_saidas = pd.DataFrame(
                [{"Categoria": k, "Total_R$": v} for k, v in saidas_dict.items()]
            ).sort_values("Total_R$", ascending=False)

            st.markdown("#### 📥 Entradas (Lado Esquerdo)  •  📤 Saídas (Lado Direito)")
            ctab1, ctab2 = st.columns(2)
            with ctab1:
                st.dataframe(df_entradas, use_container_width=True)
            with ctab2:
                st.dataframe(df_saidas, use_container_width=True)

            # ======= NOVO: gráfico de barras comparativo =======
            try:
                import plotly.express as px
                bars = (
                    pd.concat([
                        df_entradas.assign(Lado="Entradas"),
                        df_saidas.assign(Lado="Saídas")
                    ], ignore_index=True)
                    .sort_values("Total_R$", ascending=False)
                )
                fig = px.bar(
                    bars, x="Categoria", y="Total_R$", color="Lado",
                    barmode="group", text_auto=".2f",
                    title="Entradas x Saídas (período)"
                )
                fig.update_layout(height=460, font=dict(family="Inter, sans-serif"))
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass

            # (Opcional) Tabela de produtos — mantida
            st.markdown("#### Produtos — Compras x Vendas x Margem")
            resumo = pd.DataFrame({
                "Produto": ["Bolão","Raspadinha","Loteria Federal"],
                "Compra_R$":[df_all["Total_Compra_Bolao"].sum(),
                            df_all["Total_Compra_Raspadinha"].sum(),
                            df_all["Total_Compra_LoteriaFederal"].sum()],
                "Venda_R$":[df_all["Total_Venda_Bolao"].sum(),
                            df_all["Total_Venda_Raspadinha"].sum(),
                            df_all["Total_Venda_LoteriaFederal"].sum()],
            })
            resumo["Margem_R$"] = resumo["Venda_R$"] - resumo["Compra_R$"]
            st.dataframe(resumo, use_container_width=True)

            # Download
            st.download_button("⬇️ Baixar fechamentos (CSV)",
                            data=df_all.to_csv(index=False).encode("utf-8"),
                            file_name="fechamentos_periodo.csv", mime="text/csv")


    # ----------------- TAB 3 — CONFERÊNCIA DE FECHAMENTOS -----------------
    with tab3:
        import plotly.express as px
        st.markdown("#### 🧾 Conferência de Fechamentos (Δ Encerrante por dia)")

        c1, c2, c3 = st.columns(3)
        with c1: pdv_conf = st.selectbox("PDV", ["Todos"] + list(FECH_PDV.keys()), key="conf_pdv")
        with c2: conf_ini = st.date_input("Início", value=obter_date_brasilia() - timedelta(days=7), key="conf_ini")
        with c3: conf_fim = st.date_input("Fim", value=obter_date_brasilia(), key="conf_fim")

        frames = []
        for pdv, sheet in FECH_PDV.items():
            if pdv_conf != "Todos" and pdv != pdv_conf: 
                continue
            try:
                df = pd.DataFrame(buscar_dados(spreadsheet, sheet) or [])
                if df.empty: 
                    continue
                df["Data_Fechamento"] = pd.to_datetime(df["Data_Fechamento"], errors="coerce").dt.date
                df = df[(df["Data_Fechamento"] >= conf_ini) & (df["Data_Fechamento"] <= conf_fim)]
                if df.empty: 
                    continue
                df["PDV"] = pdv
                frames.append(df)
            except Exception as e:
                st.warning(f"⚠️ Erro ao buscar {sheet}: {e}")

        if not frames:
            st.info("Sem fechamentos no período selecionado.")
        else:
            df_all = _normalize_fech(pd.concat(frames, ignore_index=True))
            df_all["Status"] = np.where(df_all["Delta_Enc_Calc"].abs() < 0.005, "OK", "Divergente")
            view_cols = [
                "Data_Fechamento","PDV","Operador",
                "Encerrante_Relatorio","Troco_Anterior","Suprimento_Cofre","Total_Vendas_Soma",
                "Movimentacao_Cielo","Pix_Saida","Cheques_Recebidos","Pagamento_Premios","Vales_Despesas",
                "Retirada_Cofre","Total_Compra_Bolao","Retirada_CaixaInterno","Dinheiro_Gaveta_Final",
                "Left_Enc","Right_Enc","Delta_Enc_Calc","Status"
            ]
            st.dataframe(df_all[view_cols].sort_values(["Data_Fechamento","PDV"], ascending=[False, True]),
                         use_container_width=True)

            try:
                gdf = df_all.groupby("Data_Fechamento", as_index=False)["Delta_Enc_Calc"].sum()
                fig = px.bar(gdf, x="Data_Fechamento", y="Delta_Enc_Calc", text_auto=".2f",
                             title="Δ Encerrante por dia (soma)")
                fig.update_layout(height=380, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass

    # ------------------- TAB 4 — SINCRONIZAÇÃO -------------------
    with tab4:
        st.markdown("#### 🔄 Sincronizar Estoque a partir dos Fechamentos")
        s1, s2, s3 = st.columns(3)
        with s1: pdv_sinc = st.selectbox("PDV", list(FECH_PDV.keys()), key="sinc_pdv")
        with s2: ini_s = st.date_input("Início", value=obter_date_brasilia() - timedelta(days=7), key="sinc_ini")
        with s3: fim_s = st.date_input("Fim", value=obter_date_brasilia(), key="sinc_fim")

        if st.button("⚙️ Sincronizar estoque com base nos fechamentos", use_container_width=True):
            try:
                sheet = FECH_PDV[pdv_sinc]
                df = pd.DataFrame(buscar_dados(spreadsheet, sheet) or [])
                if df.empty: 
                    st.info("Nenhum fechamento encontrado."); 
                    return
                df["Data_Fechamento"] = pd.to_datetime(df["Data_Fechamento"], errors="coerce").dt.date
                df = df[(df["Data_Fechamento"] >= ini_s) & (df["Data_Fechamento"] <= fim_s)]
                if df.empty: 
                    st.info("Sem fechamentos no período informado."); 
                    return

                df_mov_exist = _load_mov()
                chaves_exist = set(df_mov_exist.get("Chave_Sync", []).tolist())

                ws = get_or_create_worksheet(spreadsheet, SHEET_MOV, HEADERS_MOV)
                add_count = 0
                for _, row in df.iterrows():
                    data = str(row.get("Data_Fechamento")); hora = obter_horario_brasilia()
                    compras = [("Bolão", float(row.get("Qtd_Compra_Bolao",0)), float(row.get("Custo_Unit_Bolao",0))),
                               ("Raspadinha", float(row.get("Qtd_Compra_Raspadinha",0)), float(row.get("Custo_Unit_Raspadinha",0))),
                               ("Loteria Federal", float(row.get("Qtd_Compra_LoteriaFederal",0)), float(row.get("Custo_Unit_LoteriaFederal",0)))]
                    vendas  = [("Bolão", float(row.get("Qtd_Venda_Bolao",0)), float(row.get("Preco_Unit_Bolao",0))),
                               ("Raspadinha", float(row.get("Qtd_Venda_Raspadinha",0)), float(row.get("Preco_Unit_Raspadinha",0))),
                               ("Loteria Federal", float(row.get("Qtd_Venda_LoteriaFederal",0)), float(row.get("Preco_Unit_LoteriaFederal",0)))]
                    for prod,qtd,vu in compras:
                        if qtd>0:
                            chave=f"{data}|{pdv_sinc}|{prod}|ENT|{qtd}|{vu}"
                            if chave not in chaves_exist:
                                ws.append_row([data,hora,pdv_sinc,prod,"Entrada",qtd,vu,qtd*vu,"sync-fech",sheet,chave])
                                chaves_exist.add(chave); add_count+=1
                    for prod,qtd,vu in vendas:
                        if qtd>0:
                            chave=f"{data}|{pdv_sinc}|{prod}|SAI|{qtd}|{vu}"
                            if chave not in chaves_exist:
                                ws.append_row([data,hora,pdv_sinc,prod,"Venda",qtd,vu,qtd*vu,"sync-fech",sheet,chave])
                                chaves_exist.add(chave); add_count+=1

                st.success(f"✅ Sincronização concluída: {add_count} movimentos incluídos.")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"❌ Erro na sincronização: {e}")

    # ------------------- TAB 5 — EDITAR/REMOVER -------------------
    with tab5:
        st.markdown("#### ✏️ Editar ou Remover Fechamento (PDV + Data)")

        c1, c2 = st.columns(2)
        with c1: 
            pdv_ed = st.selectbox("PDV", list(FECH_PDV.keys()), key="ed_pdv")
        with c2:
            try:
                sheet_name = _sheet_for_pdv(pdv_ed)
                df_dates = pd.DataFrame(buscar_dados(spreadsheet, sheet_name) or [])
                if df_dates.empty or "Data_Fechamento" not in df_dates.columns:
                    st.warning("Nenhum fechamento encontrado para este PDV."); 
                    st.stop()
                df_dates["Data_Fechamento"] = pd.to_datetime(df_dates["Data_Fechamento"], errors="coerce").dt.date
                datas_pdv = sorted(df_dates["Data_Fechamento"].dropna().unique().tolist(), reverse=True)
            except Exception as e:
                st.error(f"Erro ao carregar datas: {e}"); 
                st.stop()
            data_sel = st.selectbox("Data", datas_pdv, format_func=lambda d: d.strftime("%d/%m/%Y"), key="ed_data")

        df_reg = df_dates[(df_dates["PDV"].astype(str) == pdv_ed) & (df_dates["Data_Fechamento"] == data_sel)]
        if df_reg.empty:
            st.info("Registro não encontrado para o PDV/Data selecionados."); 
            st.stop()
        rec = _normalize_fech(df_reg).iloc[0].to_dict()

        # automáticos do dia
        ret_caixa_interno, _ = _get_sangrias_do_dia(pdv_ed, data_sel)
        supr_cofre_dia, _  = _get_suprimentos_cofre_do_dia(pdv_ed, data_sel)
        saldo_ant_recalc    = _get_saldo_anterior(pdv_ed, data_sel)
        troco_anterior      = _get_troco_anterior(pdv_ed, data_sel)

        with st.form("form_editar_fechamento", clear_on_submit=False):
            st.markdown("##### Dados do registro")
            ctop1, ctop2, ctop3 = st.columns(3)
            with ctop1: 
                operador_ed = st.text_input("Operador", value=str(rec.get("Operador","")))
            with ctop2: 
                st.text_input("Retirada p/ Caixa Interno (auto)", value=f"R$ {ret_caixa_interno:,.2f}", disabled=True)
            with ctop3: 
                st.text_input("Suprimento do Cofre (auto)", value=f"R$ {supr_cofre_dia:,.2f}", disabled=True)

            st.markdown("##### Compras")
            cb1, cb2, cb3 = st.columns(3)
            with cb1: 
                qtd_comp_bolao = st.number_input("Qtd Compra Bolão (un)", min_value=0, step=1, format="%d",
                                                 value=int(rec.get("Qtd_Compra_Bolao",0)))
            with cb2: 
                custo_unit_bolao = st.number_input("Custo Unit Bolão (R$)", min_value=0.0, step=1.0, format="%.2f",
                                                   value=float(rec.get("Custo_Unit_Bolao",0)))
            with cb3:
                tot_comp_bolao = qtd_comp_bolao * custo_unit_bolao
                st.metric("Total Compra Bolão", f"R$ {tot_comp_bolao:,.2f}")

            # (raspadinha/federal mantidas para compatibilidade)
            cr1, cr2, cr3 = st.columns(3)
            with cr1: 
                qtd_comp_rasp = st.number_input("Qtd Compra Raspadinha (un)", min_value=0, step=1, format="%d",
                                                value=int(rec.get("Qtd_Compra_Raspadinha",0)))
            with cr2: 
                custo_unit_rasp = st.number_input("Custo Unit Raspadinha (R$)", min_value=0.0, step=1.0, format="%.2f",
                                                  value=float(rec.get("Custo_Unit_Raspadinha",0)))
            with cr3:
                tot_comp_rasp = qtd_comp_rasp * custo_unit_rasp
                st.metric("Total Compra Raspadinha", f"R$ {tot_comp_rasp:,.2f}")

            cl1, cl2, cl3 = st.columns(3)
            with cl1: 
                qtd_comp_fed = st.number_input("Qtd Compra Loteria Federal (un)", min_value=0, step=1, format="%d",
                                               value=int(rec.get("Qtd_Compra_LoteriaFederal",0)))
            with cl2: 
                custo_unit_fed = st.number_input("Custo Unit Loteria Federal (R$)", min_value=0.0, step=1.0, format="%.2f",
                                                 value=float(rec.get("Custo_Unit_LoteriaFederal",0)))
            with cl3:
                tot_comp_fed = qtd_comp_fed * custo_unit_fed
                st.metric("Total Compra Loteria Federal", f"R$ {tot_comp_fed:,.2f}")

            st.markdown("##### Vendas")
            vb1, vb2, vb3 = st.columns(3)
            with vb1: 
                qtd_venda_bolao = st.number_input("Qtd Venda Bolão (un)", min_value=0, step=1, format="%d",
                                                  value=int(rec.get("Qtd_Venda_Bolao",0)))
            with vb2: 
                preco_unit_bolao = st.number_input("Preço Unit Bolão (R$)", min_value=0.0, step=1.0, format="%.2f",
                                                   value=float(rec.get("Preco_Unit_Bolao",0)))
            with vb3:
                tot_venda_bolao = qtd_venda_bolao * preco_unit_bolao
                st.metric("Total Venda Bolão", f"R$ {tot_venda_bolao:,.2f}")

            vr1, vr2, vr3 = st.columns(3)
            with vr1: 
                qtd_venda_rasp = st.number_input("Qtd Venda Raspadinha (un)", min_value=0, step=1, format="%d",
                                                 value=int(rec.get("Qtd_Venda_Raspadinha",0)))
            with vr2: 
                preco_unit_rasp = st.number_input("Preço Unit Raspadinha (R$)", min_value=0.0, step=1.0, format="%.2f",
                                                  value=float(rec.get("Preco_Unit_Raspadinha",0)))
            with vr3:
                tot_venda_rasp = qtd_venda_rasp * preco_unit_rasp
                st.metric("Total Venda Raspadinha", f"R$ {tot_venda_rasp:,.2f}")

            vf1, vf2, vf3 = st.columns(3)
            with vf1: 
                qtd_venda_fed = st.number_input("Qtd Venda Loteria Federal (un)", min_value=0, step=1, format="%d",
                                                value=int(rec.get("Qtd_Venda_LoteriaFederal",0)))
            with vf2: 
                preco_unit_fed = st.number_input("Preço Unit Loteria Federal (R$)", min_value=0.0, step=1.0, format="%.2f",
                                                 value=float(rec.get("Preco_Unit_LoteriaFederal",0)))
            with vf3:
                tot_venda_fed = qtd_venda_fed * preco_unit_fed
                st.metric("Total Venda Loteria Federal", f"R$ {tot_venda_fed:,.2f}")

            total_vendas = tot_venda_bolao + tot_venda_rasp + tot_venda_fed

            st.markdown("##### Outras movimentações")
            om1, om2, om3 = st.columns(3)
            with om1: 
                movimentacao_cielo = st.number_input("Movimentação Cielo (R$)", min_value=0.0, step=50.0, format="%.2f",
                                                     value=float(rec.get("Movimentacao_Cielo",0)))
            with om2: 
                pagamento_premios = st.number_input("Pagamento de Prêmios (R$)", min_value=0.0, step=50.0, format="%.2f",
                                                    value=float(rec.get("Pagamento_Premios",0)))
            with om3: 
                vales_despesas = st.number_input("Vales/Despesas (R$)", min_value=0.0, step=50.0, format="%.2f",
                                                 value=float(rec.get("Vales_Despesas",0)))

            om4, om5, om6 = st.columns(3)
            with om4: 
                pix_saida = st.number_input("PIX Saída (R$)", min_value=0.0, step=50.0, format="%.2f",
                                            value=float(rec.get("Pix_Saida",0)))
            with om5: 
                retirada_cofre = st.number_input("Retirada para Cofre (R$)", min_value=0.0, step=50.0, format="%.2f",
                                                 value=float(rec.get("Retirada_Cofre",0)))
            with om6: 
                cheques_recebidos = st.number_input("Cheques Recebidos (R$)", min_value=0.0, step=50.0, format="%.2f",
                                                    value=float(rec.get("Cheques_Recebidos",0)))

            st.markdown("##### Encerrante / Caixa")
            cenc1, cenc2, cenc3 = st.columns(3)
            with cenc1: 
                encerrante_relatorio = st.number_input("Encerrante do Relatório (±)", step=50.0, format="%.2f",
                                                       value=float(rec.get("Encerrante_Relatorio",0)))
            with cenc2: 
                st.text_input("Troco do dia anterior (auto)", value=f"R$ {troco_anterior:,.2f}", disabled=True)
            with cenc3: 
                dg_final = st.number_input("Dinheiro em Gaveta (final do dia) (R$)", min_value=0.0, step=50.0, format="%.2f",
                                           value=float(rec.get("Dinheiro_Gaveta_Final",0)))

            # Cálculos (mantidos para salvar, mas sem mostrar os cards tradicionais)
            saldo_final_calc = (
                _to_float(saldo_ant_recalc)
                + (_to_float(total_vendas) - _to_float(movimentacao_cielo))
                - _to_float(pagamento_premios) - _to_float(vales_despesas)
                - _to_float(pix_saida) - _to_float(retirada_cofre) - _to_float(ret_caixa_interno)
            )
            diferenca = _to_float(dg_final) - _to_float(saldo_final_calc)

            # Conciliação do Encerrante (regra acordada) — ÚNICO indicador exibido
            left_enc  = _to_float(encerrante_relatorio) + _to_float(troco_anterior) + _to_float(supr_cofre_dia) + _to_float(total_vendas)
            right_enc = _to_float(movimentacao_cielo) + _to_float(pix_saida) + _to_float(cheques_recebidos) \
                        + _to_float(pagamento_premios) + _to_float(vales_despesas) + _to_float(retirada_cofre) \
                        + _to_float(tot_comp_bolao) + _to_float(ret_caixa_interno) + _to_float(dg_final)
            delta_enc = left_enc - right_enc

            st.markdown("##### Saldo Calculado do Caixa (Encerrante)")
            st.metric("Encerrante (deve ser R$ 0,00)", f"R$ {delta_enc:,.2f}")
            st.caption("Regra: (Encerrante Relatório + Troco anterior + Suprimentos do Cofre + Vendas) − "
                       "(Cielo + PIX + Cheques + Prêmios + Despesas + Retirada p/ Cofre + Compra Bolão + "
                       "Retirada p/ Caixa Interno + Dinheiro em Gaveta).")

            col_save, col_del = st.columns([2,1])
            salvar = col_save.form_submit_button("💾 Salvar alterações", use_container_width=True)
            excluir = col_del.form_submit_button("🗑️ Remover este fechamento", use_container_width=True)

        ws_pdv = get_or_create_worksheet(spreadsheet, _sheet_for_pdv(pdv_ed), HEADERS_FECHAMENTO)
        row_idx = _find_row_by_pdv_date(ws_pdv, pdv_ed, data_sel)

        if salvar:
            if row_idx is None:
                st.error("Não foi possível localizar a linha no Sheets para atualizar.")
            else:
                try:
                    row = [
                        str(data_sel), pdv_ed, operador_ed,
                        int(qtd_comp_bolao), float(custo_unit_bolao), float(tot_comp_bolao),
                        int(qtd_comp_rasp), float(custo_unit_rasp), float(tot_comp_rasp),
                        int(qtd_comp_fed), float(custo_unit_fed), float(tot_comp_fed),
                        int(qtd_venda_bolao), float(preco_unit_bolao), float(tot_venda_bolao),
                        int(qtd_venda_rasp), float(preco_unit_rasp), float(tot_venda_rasp),
                        int(qtd_venda_fed), float(preco_unit_fed), float(tot_venda_fed),
                        float(movimentacao_cielo), float(pagamento_premios), float(vales_despesas), float(pix_saida),
                        float(retirada_cofre), float(ret_caixa_interno), float(dg_final),
                        float(saldo_ant_recalc), float(saldo_final_calc), float(diferenca),
                        float(encerrante_relatorio), float(cheques_recebidos), float(supr_cofre_dia), float(troco_anterior), float(delta_enc)
                    ]
                    ws_pdv.update(f"A{row_idx}", [row])
                    st.success("✅ Fechamento atualizado com sucesso.")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"❌ Erro ao atualizar: {e}")

        if excluir:
            if st.checkbox("Confirmo que desejo remover este fechamento definitivamente."):
                if row_idx is None:
                    st.error("Não foi possível localizar a linha no Sheets para remover.")
                else:
                    try:
                        ws_pdv.delete_rows(row_idx)
                        st.success("✅ Fechamento removido.")
                        st.cache_data.clear(); st.experimental_rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao remover: {e}")
            else:
                st.info("Marque a confirmação para habilitar a remoção.")





# ------------------------------------------------------------
def render_operacoes_caixa(spreadsheet):
    import pandas as pd
    from datetime import timedelta
    from uuid import uuid4
    from decimal import Decimal

    st.subheader("💳 Operações do Caixa Interno")
    
    PDV_UI_TO_CODE = {
        "Pdv1 - terminal 051650 - bruna": "PDV 1",
        "Pdv2 - terminal 030949 - Karina": "PDV 2",
    }

    ABA_CAIXA = "Operacoes_Caixa"
    HEADERS_CAIXA = ["Data","Hora","Operador","Tipo_Operacao","Cliente","CPF","Valor_Bruto","Taxa_Cliente","Taxa_Banco","Valor_Liquido","Lucro","Status","Data_Vencimento_Cheque","Taxa_Percentual","Observacoes"]
    ABA_MOV_PDV = "Movimentacoes_PDV"
    HEADERS_MOV_PDV = ["Data","Hora","PDV","Tipo_Mov","Valor","Vinculo_ID","Operador","Observacoes"]
    ABA_COFRE = "Operacoes_Cofre"
    HEADERS_COFRE = ["Data","Hora","Operador","Tipo","Categoria","Origem","Destino","Valor","Observacoes","Status","Vinculo_ID"]

    # --------- helpers ---------
    def _gerar_vinc(prefix="CXINT"):
        return f"{prefix}-{uuid4().hex[:8]}"

    def _to_float(x):
        try:
            if isinstance(x, Decimal):
                return float(x)
            return float(x)
        except Exception:
            return 0.0

    def _pct(taxa, base):
        basef = _to_float(base)
        return 0.0 if basef == 0 else (_to_float(taxa) / basef) * 100.0

    def _try_registrar_no_fechamento_ret_caixa_interno(data_mov, pdv_code, valor, vinculo_id, obs):
        ws_name = "Fechamentos_PDV1" if pdv_code == "PDV 1" else "Fechamentos_PDV2"
        try:
            dados = buscar_dados(spreadsheet, ws_name) or []
        except Exception:
            dados = None

        if dados:
            df = pd.DataFrame(dados)
            if not df.empty:
                cols = list(df.columns)
                low  = {c: c.lower() for c in cols}
                col_data = next((c for c in cols if "data" in low[c]), None)
                col_pdv  = next((c for c in cols if "pdv"  in low[c]), None)
                if "Retirada_CaixaInterno" in cols:
                    col_ret_int = "Retirada_CaixaInterno"
                else:
                    col_ret_int = next((c for c in cols if "retirada" in low[c] and "interno" in low[c]), None)

                if col_data and col_pdv and col_ret_int:
                    ws = get_or_create_worksheet(spreadsheet, ws_name, cols)
                    nova = {c: "" for c in cols}
                    nova[col_data]    = str(data_mov)
                    nova[col_pdv]     = pdv_code
                    nova[col_ret_int] = _to_float(valor)

                    col_vinc = next((c for c in cols if "vinculo" in low[c]), None)
                    if col_vinc: nova[col_vinc] = vinculo_id
                    col_obs  = next((c for c in cols if "observ" in low[c]), None)
                    if col_obs:  nova[col_obs]  = f"PDV → Caixa Interno. {obs or ''}"

                    ws.append_row([nova.get(c, "") for c in cols])
                    return True

        ws_fb = get_or_create_worksheet(
            spreadsheet,
            "Fechamento_PDV_Lancamentos",
            ["Data","PDV","Tipo","Valor","Vinculo_ID","Observacoes"]
        )
        ws_fb.append_row([
            str(data_mov), pdv_code, "Retirada Caixa Interno",
            _to_float(valor), vinculo_id, f"PDV → Caixa Interno. {obs or ''}"
        ])
        return False

    try:
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["💳 Saque Cartão", "📄 Troca de Cheques", "🔄 Suprimento Caixa", "📊 Histórico", "🗓️ Fechamento Caixa Interno"])
        
        # ============== TAB 1 — Saque Cartão ==============
        with tab1:
            st.markdown("### 💳 Saque com Cartão")
            with st.form("form_saque_cartao", clear_on_submit=False):
                operador_selecionado = st.selectbox("👤 Operador Responsável", ["Bruna","Karina","Edson","Robson","Adiel","Lucas","Ana Paula","Fernanda","CRIS"])
                col1, col2 = st.columns(2)
                with col1:
                    # >>> AJUSTE: Cielo Posto integrado ao Tipo de Cartão
                    tipo_cartao = st.selectbox(
                        "Tipo de Cartão",
                        ["Débito", "Crédito", "Cielo Posto (Débito)", "Cielo Posto (Crédito)"]
                    )
                    valor = st.number_input("Valor do Saque (R$)", min_value=0.01, step=50.0)
                    nome = st.text_input("Nome do Cliente (Opcional)")
                with col2:
                    cpf = st.text_input("CPF do Cliente (Opcional)")
                    observacoes = st.text_area("Observações")

                # Deriva base e flag Cielo
                is_cielo = "Cielo Posto" in tipo_cartao
                tipo_base = "Débito" if "Débito" in tipo_cartao else "Crédito"

                col_sim, col_conf = st.columns([1, 1])
                with col_sim:
                    simular = st.form_submit_button("🧮 Simular Operação", use_container_width=True)

                if simular and valor > 0:
                    try:
                        if is_cielo:
                            calc = {"taxa_cliente": 0.0, "taxa_banco": 0.0, "lucro": 0.0, "valor_liquido": _to_float(valor)}
                        else:
                            calc = calcular_taxa_cartao_debito(valor) if tipo_base == "Débito" else calcular_taxa_cartao_credito(valor)

                        st.markdown("---")
                        st.markdown(f"### ✅ Simulação - Cartão {tipo_base}")
                        col_res1, col_res2 = st.columns(2)
                        with col_res1:
                            st.metric("Taxa Percentual", f"{_pct(calc['taxa_cliente'], valor):.2f}%")
                            st.metric("Taxa em Valores", f"R$ {_to_float(calc['taxa_cliente']):,.2f}")
                        with col_res2:
                            st.metric("💵 Valor a Entregar", f"R$ {_to_float(calc['valor_liquido']):,.2f}")
                            st.info("💡 Cielo Posto: taxa 0%." if is_cielo else "💡 Taxa de 1% (Débito) | 5,33% (Crédito)")

                        obs_final = (f"{observacoes} | Forma: Cielo Posto".strip() if is_cielo and observacoes
                                     else ("Forma: Cielo Posto" if is_cielo else (observacoes or "")))

                        st.session_state.simulacao_atual = {
                            "tipo": f"Saque Cartão {tipo_base}",          # mantém a categoria original
                            "dados": calc,
                            "valor_bruto": _to_float(valor),
                            "nome": nome or "Não informado",
                            "cpf": cpf or "Não informado",
                            "observacoes": obs_final
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
                            sim = st.session_state.simulacao_atual
                            ws = get_or_create_worksheet(spreadsheet, ABA_CAIXA, HEADERS_CAIXA)
                            ws.append_row([
                                obter_data_brasilia(), obter_horario_brasilia(), operador_selecionado,
                                sim["tipo"], sim["nome"], sim["cpf"], _to_float(sim["valor_bruto"]),
                                _to_float(sim["dados"]["taxa_cliente"]), _to_float(sim["dados"]["taxa_banco"]), _to_float(sim["dados"]["valor_liquido"]),
                                _to_float(sim["dados"]["lucro"]), "Concluído", "", f"{_pct(sim['dados']['taxa_cliente'], sim['valor_bruto']):.2f}%",
                                sim["observacoes"]
                            ])
                            st.success(f"✅ {sim['tipo']} de R$ {sim['valor_bruto']:,.2f} registrado!")
                            del st.session_state.simulacao_atual
                            st.cache_data.clear()
                    except Exception as e:
                        st.error(f"❌ Erro ao salvar operação: {str(e)}")
        
        # ============== TAB 2 — Troca de Cheques ==============
        with tab2:
            st.markdown("### 📄 Troca de Cheques")
            with st.form("form_troca_cheque", clear_on_submit=False):
                operador_selecionado_cheque = st.selectbox("👤 Operador Responsável", ["Bruna","Karina","Edson","Robson","Adiel","Lucas","Ana Paula","Fernanda","CRIS"], key="op_cheque")
                col1, col2 = st.columns(2)
                with col1:
                    tipo_cheque = st.selectbox("Tipo de Cheque", ["Cheque à Vista", "Cheque Pré-datado", "Cheque com Taxa Manual"])
                    valor = st.number_input("Valor do Cheque (R$)", min_value=0.01, step=100.0, key="valor_cheque")
                    nome = st.text_input("Nome do Cliente (Opcional)", key="nome_cheque")
                with col2:
                    cpf = st.text_input("CPF do Cliente (Opcional)", key="cpf_cheque")
                    observacoes = st.text_area("Observações", key="obs_cheque")
                dias = 0; taxa_manual = 0; data_venc = ""
                if tipo_cheque == "Cheque Pré-datado":
                    data_vencimento = st.date_input("Data de Vencimento", value=obter_date_brasilia())
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
                            calc = calcular_taxa_cheque_vista(valor); data_venc = obter_data_brasilia()
                        elif tipo_cheque == "Cheque Pré-datado":
                            calc = calcular_taxa_cheque_pre_datado(valor, dias)
                        else:
                            calc = calcular_taxa_cheque_manual(valor, taxa_manual); data_venc = obter_data_brasilia()
                        st.markdown("---"); st.markdown(f"### ✅ Simulação - {tipo_cheque}")
                        col_res1, col_res2 = st.columns(2)
                        with col_res1:
                            st.metric("Taxa Percentual", f"{_pct(calc['taxa_cliente'], valor):.2f}%")
                            st.metric("Taxa em Valores", f"R$ {_to_float(calc['taxa_cliente']):,.2f}")
                        with col_res2:
                            st.metric("💵 Valor a Entregar", f"R$ {_to_float(calc['valor_liquido']):,.2f}")
                        st.session_state.simulacao_atual = {
                            "tipo": tipo_cheque, "dados": calc, "valor_bruto": _to_float(valor),
                            "nome": nome or "Não informado", "cpf": cpf or "Não informado",
                            "observacoes": observacoes, "data_vencimento": data_venc
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
                            sim = st.session_state.simulacao_atual
                            ws = get_or_create_worksheet(spreadsheet, ABA_CAIXA, HEADERS_CAIXA)
                            ws.append_row([
                                obter_data_brasilia(), obter_horario_brasilia(), operador_selecionado_cheque,
                                sim["tipo"], sim["nome"], sim["cpf"], _to_float(sim["valor_bruto"]),
                                _to_float(sim["dados"]["taxa_cliente"]), _to_float(sim["dados"]["taxa_banco"]), _to_float(sim["dados"]["valor_liquido"]),
                                _to_float(sim["dados"]["lucro"]), "Concluído", sim["data_vencimento"],
                                f"{_pct(sim['dados']['taxa_cliente'], sim['valor_bruto']):.2f}%", sim["observacoes"]
                            ])
                            st.success(f"✅ {sim['tipo']} de R$ {sim['valor_bruto']:,.2f} registrado!")
                            del st.session_state.simulacao_atual
                            st.cache_data.clear()
                    except Exception as e:
                        st.error(f"❌ Erro ao salvar operação: {str(e)}")
        
        # ============== TAB 3 — Suprimento do Caixa ==============
        with tab3:
            st.markdown("### 🔄 Suprimento do Caixa")
            with st.form("form_suprimento", clear_on_submit=True):
                operador_selecionado_suprimento = st.selectbox("👤 Operador Responsável", ["Bruna","Karina","Edson","Robson","Adiel","Lucas","Ana Paula","Fernanda","CRIS"], key="op_suprimento")
                valor_suprimento = st.number_input("Valor do Suprimento (R$)", min_value=0.01, step=100.0)
                origem_suprimento_ui = st.selectbox("Origem do Suprimento", ["Cofre Principal"] + list(PDV_UI_TO_CODE.keys()))
                pdv_code_origem = None
                if origem_suprimento_ui == "Cofre Principal":
                    origem_normalizada = "Cofre Principal"
                else:
                    pdv_code_origem = PDV_UI_TO_CODE[origem_suprimento_ui]
                    origem_normalizada = f"Caixa Lotérica - {pdv_code_origem}"
                observacoes_sup = st.text_area("Observações do Suprimento")

                if st.form_submit_button("💰 Registrar Suprimento", use_container_width=True):
                    try:
                        ws_cx = get_or_create_worksheet(spreadsheet, ABA_CAIXA, HEADERS_CAIXA)
                        data_mov = obter_data_brasilia()
                        hora_mov = obter_horario_brasilia()
                        vinculo_id = _gerar_vinc("CXINT_SUPR")

                        # 1) Lança no Caixa Interno
                        ws_cx.append_row([
                            data_mov, hora_mov, operador_selecionado_suprimento,
                            "Suprimento", "Sistema", "N/A",
                            _to_float(valor_suprimento), 0, 0, _to_float(valor_suprimento), 0,
                            "Concluído", "", "0.00%",
                            f"Origem: {origem_normalizada}. Vínculo {vinculo_id}. {observacoes_sup or ''}"
                        ])

                        # 2) SE a origem for COFRE PRINCIPAL -> espelha no COFRE como SAÍDA (Transferência p/ Caixa Interno)
                        if origem_suprimento_ui == "Cofre Principal":
                            ws_cofre = get_or_create_worksheet(spreadsheet, ABA_COFRE, HEADERS_COFRE)
                            try:
                                exist = buscar_dados(spreadsheet, ABA_COFRE) or []
                                df_exist = pd.DataFrame(exist)
                                dup = (not df_exist.empty and "Vinculo_ID" in df_exist.columns
                                       and df_exist["Vinculo_ID"].astype(str).eq(vinculo_id).any())
                            except Exception:
                                dup = False
                            if not dup:
                                ws_cofre.append_row([
                                    str(data_mov), str(hora_mov), st.session_state.get("nome_usuario",""),
                                    "Saída", "Transferência para Caixa Interno", "Cofre Principal", "Caixa Interno",
                                    _to_float(valor_suprimento),
                                    f"Gerado por Suprimento do Caixa Interno. Vínculo {vinculo_id}. {observacoes_sup or ''}",
                                    "Concluído", vinculo_id
                                ])

                        # 3) SE a origem for PDV -> já havia integração PDV + Fechamento
                        if pdv_code_origem in ["PDV 1","PDV 2"]:
                            ws_mov = get_or_create_worksheet(spreadsheet, ABA_MOV_PDV, HEADERS_MOV_PDV)
                            mov_exist = buscar_dados(spreadsheet, ABA_MOV_PDV) or []
                            df_mov = pd.DataFrame(mov_exist)
                            ja_existe = (not df_mov.empty and "Vinculo_ID" in df_mov.columns
                                         and df_mov["Vinculo_ID"].astype(str).eq(vinculo_id).any())
                            if not ja_existe:
                                ws_mov.append_row([
                                    str(data_mov), str(hora_mov),
                                    pdv_code_origem, "Saída p/ Caixa Interno",
                                    _to_float(valor_suprimento), vinculo_id,
                                    st.session_state.get("nome_usuario",""),
                                    f"Gerado por suprimento do Caixa Interno. {observacoes_sup or ''}"
                                ])
                            _try_registrar_no_fechamento_ret_caixa_interno(
                                data_mov, pdv_code_origem, valor_suprimento, vinculo_id, observacoes_sup
                            )

                        st.success(f"✅ Suprimento de R$ {valor_suprimento:,.2f} registrado com sucesso!")
                        st.cache_data.clear()

                    except Exception as e:
                        st.error(f"❌ Erro ao registrar suprimento: {str(e)}")
        
        # ============== TAB 4 — Histórico ==============
        with tab4:
            st.markdown("### 📊 Histórico de Operações")
            try:
                col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
                with col_filtro1:
                    if st.button("📅 Filtrar por Data"):
                        st.session_state.mostrar_filtro_data = not st.session_state.get("mostrar_filtro_data", False)
                if st.session_state.get("mostrar_filtro_data", False):
                    col_data1, col_data2 = st.columns(2)
                    with col_data1:
                        data_inicio = st.date_input("Data Início", value=obter_date_brasilia() - timedelta(days=7))
                    with col_data2:
                        data_fim = st.date_input("Data Fim", value=obter_date_brasilia())
                with col_filtro2:
                    tipo_operacao_filtro = st.selectbox("Tipo de Operação", ["Todos", "Saque Cartão Débito", "Saque Cartão Crédito", "Troca Cheque à Vista", "Troca Cheque Pré-datado", "Suprimento"])
                operacoes_data = buscar_dados(spreadsheet, ABA_CAIXA)
                if operacoes_data:
                    df_operacoes = pd.DataFrame(normalizar_dados_inteligente(operacoes_data))
                    if tipo_operacao_filtro != "Todos":
                        df_operacoes = df_operacoes[df_operacoes["Tipo_Operacao"] == tipo_operacao_filtro]
                    if st.session_state.get("mostrar_filtro_data", False):
                        try:
                            df_operacoes["Data"] = pd.to_datetime(df_operacoes["Data"], errors="coerce")
                            df_operacoes = df_operacoes[(df_operacoes["Data"] >= pd.to_datetime(data_inicio)) & (df_operacoes["Data"] <= pd.to_datetime(data_fim))]
                        except Exception:
                            st.warning("⚠️ Erro ao aplicar filtro de data.")
                    if not df_operacoes.empty:
                        try:
                            if {"Data","Hora"}.issubset(df_operacoes.columns):
                                df_operacoes = df_operacoes.sort_values(by=["Data","Hora"], ascending=False)
                        except Exception:
                            pass
                        st.dataframe(df_operacoes, use_container_width=True)
                        st.markdown("---"); st.markdown("### 📈 Estatísticas do Período")
                        c1,c2,c3 = st.columns(3)
                        with c1: st.metric("Total de Operações", len(df_operacoes))
                        with c2:
                            if "Valor_Bruto" in df_operacoes.columns: st.metric("Total Movimentado", f"R$ {df_operacoes['Valor_Bruto'].sum():,.2f}")
                        with c3:
                            if "Taxa_Cliente" in df_operacoes.columns: st.metric("Total em Taxas", f"R$ {df_operacoes['Taxa_Cliente'].sum():,.2f}")
                    else:
                        st.info("Nenhuma operação encontrada com os filtros aplicados.")
                else:
                    st.info("Nenhuma operação registrada ainda.")
            except Exception as e:
                st.error(f"❌ Erro ao carregar histórico: {str(e)}")
    
    except Exception as e:
        st.error(f"❌ Erro ao carregar operações do caixa: {str(e)}")
        st.info("🔄 Tente recarregar a página ou verifique a conexão com o Google Sheets.")









def render_dashboard_caixa(spreadsheet):
    st.subheader("💳 Dashboard Caixa Interno")

    # Flag de perfil (robusta a variações)
    is_gerente = "gerente" in str(st.session_state.get("tipo_usuario", "")).lower()

    # 1) Buscar e normalizar dados de operações
    operacoes_data = buscar_dados(spreadsheet, "Operacoes_Caixa") or []
    operacoes_data_normalizada = normalizar_dados_inteligente(operacoes_data)
    df_operacoes = pd.DataFrame(operacoes_data_normalizada)

    # Tipagem defensiva
    if not df_operacoes.empty:
        for col in ["Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro"]:
            if col in df_operacoes.columns:
                df_operacoes[col] = pd.to_numeric(df_operacoes[col], errors="coerce").fillna(0.0)
        try:
            df_operacoes["Data"] = pd.to_datetime(df_operacoes["Data"], errors="coerce").dt.date
        except Exception:
            pass

    # ================== CÁLCULO NOVO DO SALDO ==================
    TIPOS_SAQUE  = ["Saque Cartão Débito", "Saque Cartão Crédito"]
    TIPOS_CHEQUE = ["Cheque à Vista", "Cheque Pré-datado", "Cheque com Taxa Manual"]

    # 1) Saldo do dia anterior (último fechamento <= ontem)
    saldo_anterior = 0.0
    try:
        fech_data = buscar_dados(spreadsheet, "Fechamento_Diario_Caixa_Interno") or []
        if fech_data:
            df_fech = pd.DataFrame(fech_data)
            df_fech["Data_Fechamento"] = pd.to_datetime(df_fech["Data_Fechamento"], errors="coerce").dt.date
            df_fech["Saldo_Calculado_Dia"] = pd.to_numeric(df_fech.get("Saldo_Calculado_Dia", 0), errors="coerce").fillna(0.0)

            hoje_dt  = obter_date_brasilia()
            ontem_dt = hoje_dt - timedelta(days=1)

            prev = df_fech[df_fech["Data_Fechamento"] <= ontem_dt].sort_values("Data_Fechamento").tail(1)
            if not prev.empty:
                saldo_anterior = float(prev.iloc[0]["Saldo_Calculado_Dia"])
    except Exception:
        pass  # se der erro, mantém 0.0

    # 2) Somente operações de HOJE
    hoje_dt = obter_date_brasilia()
    ops_hoje = df_operacoes[df_operacoes["Data"] == hoje_dt] if not df_operacoes.empty else pd.DataFrame()

    suprimentos_hoje = ops_hoje[ops_hoje["Tipo_Operacao"] == "Suprimento"]["Valor_Bruto"].sum() if not ops_hoje.empty else 0.0
    saques_hoje      = ops_hoje[ops_hoje["Tipo_Operacao"].isin(TIPOS_SAQUE)]["Valor_Liquido"].sum() if not ops_hoje.empty else 0.0
    cheques_hoje     = ops_hoje[ops_hoje["Tipo_Operacao"].isin(TIPOS_CHEQUE)]["Valor_Liquido"].sum() if not ops_hoje.empty else 0.0

    # 3) Saldo final do card
    saldo_caixa = float(saldo_anterior + suprimentos_hoje - (saques_hoje + cheques_hoje))

    # Métricas auxiliares para os cards
    operacoes_hoje_count = int(len(ops_hoje))
    valor_saque_hoje = float(sakes if (sakes := saques_hoje + cheques_hoje) else 0.0)  # saída total do dia
    # ============================================================

    # ----------------- CARDS DE MÉTRICAS -----------------
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">
                <h3>R$ {saldo_caixa:,.2f}</h3>
                <p>💰 Saldo do Caixa</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                <h3>R$ {valor_saque_hoje:,.2f}</h3>
                <p>💳 Valor Saque Hoje</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                <h3>{operacoes_hoje_count}</h3>
                <p>📋 Operações Hoje</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        status_cor = "#38ef7d" if saldo_caixa > 2000 else "#f5576c"
        status_texto = "Normal" if saldo_caixa > 2000 else "Baixo"
        st.markdown(
            f"""
            <div class="metric-card" style="background: linear-gradient(135deg, {status_cor} 0%, {status_cor} 100%);">
                <h3>{status_texto}</h3>
                <p>🚦 Status Caixa</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ----------------- GRÁFICO (últimos 7 dias) -----------------
    if is_gerente:
        st.subheader("📊 Resumo de Operações (Últimos 7 Dias)")
        try:
            if df_operacoes.empty:
                st.info("📊 Nenhuma operação nos últimos 7 dias para exibir no gráfico.")
            else:
                # janela de 7 dias
                data_limite = obter_date_brasilia() - timedelta(days=7)
                df_recente = df_operacoes.copy()
                df_recente = df_recente[df_recente["Data"] >= data_limite]

                if df_recente.empty:
                    st.info("📊 Nenhuma operação nos últimos 7 dias para exibir no gráfico.")
                else:
                    resumo_por_tipo = df_recente.groupby("Tipo_Operacao")["Valor_Liquido"].sum().reset_index()
                    fig = px.bar(
                        resumo_por_tipo,
                        x="Tipo_Operacao",
                        y="Valor_Liquido",
                        title="Valor Líquido por Tipo de Operação",
                        labels={"Tipo_Operacao": "Tipo de Operação", "Valor_Liquido": "Valor Líquido Total (R$)"},
                        color="Tipo_Operacao",
                        text_auto=".2f",
                    )
                    fig.update_layout(showlegend=False, height=420, font=dict(family="Inter, sans-serif"))
                    st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.warning("⚠️ Erro ao carregar gráfico. Dados podem estar inconsistentes.")

    # ----------------- ALERTAS DE SALDO -----------------
    if saldo_caixa < 1000:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%); padding: 1rem; border-radius: 10px; color: white; margin: 1rem 0;">
                🚨 <strong>Atenção!</strong> Saldo do caixa está muito baixo. Solicite suprimento urgente.
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif saldo_caixa < 2000:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #ffa726 0%, #ff9800 100%); padding: 1rem; border-radius: 10px; color: white; margin: 1rem 0;">
                ⚠️ <strong>Aviso:</strong> Saldo do caixa está baixo. Considere solicitar suprimento.
            </div>
            """,
            unsafe_allow_html=True,
        )






# Gestão do Cofre integrada com Fechamento da Lotérica (PDVs)
# Gestão do Cofre integrada com Fechamento da Lotérica (PDVs)
def render_cofre(spreadsheet):
    import pandas as pd
    from decimal import Decimal
    from uuid import uuid4
    from datetime import date as _date

    st.subheader("🏦 Gestão do Cofre")

    # ---- Mapeamento de rótulos da UI para o código do PDV usado no Fechamento ----
    PDV_UI_TO_CODE = {
        "Pdv1 - terminal 051650 - bruna":  "PDV 1",
        "Pdv2 - terminal 030949 - Karina": "PDV 2",
    }
    PDV_UI_LIST = list(PDV_UI_TO_CODE.keys())

    # ---- Abas e cabeçalhos esperados nas planilhas ----
    ABA_COFRE         = "Operacoes_Cofre"
    ABA_MOV_PDV       = "Movimentacoes_PDV"
    ABA_CAIXA_INTERNO = "Operacoes_Caixa"

    HEADERS_COFRE = [
        "Data","Hora","Operador","Tipo","Categoria","Origem","Destino",
        "Valor","Observacoes","Status","Vinculo_ID"
    ]
    HEADERS_MOV_PDV = [
        "Data","Hora","PDV","Tipo_Mov","Valor","Vinculo_ID","Operador","Observacoes"
    ]
    HEADERS_CAIXA = [
        "Data","Hora","Operador","Tipo_Operacao","Cliente","CPF",
        "Valor_Bruto","Taxa_Cliente","Taxa_Banco","Valor_Liquido","Lucro",
        "Status","Data_Vencimento_Cheque","Taxa_Percentual","Observacoes"
    ]

    def _gerar_id(prefix="COFRE"):
        return f"{prefix}-{uuid4().hex[:8]}"

    # ---- Registrar também no Fechamento diário do PDV (silencioso) ----
    def _try_registrar_no_fechamento_pdv(data_mov, pdv_code, tipo_mov_pdv, valor, vinculo_id, obs):
        """
        tipo_mov_pdv: "Suprimento" (Cofre -> PDV) ou "Sangria" (PDV -> Cofre)
        Abre somente a planilha do PDV (Fechamentos_PDV1/Fechamentos_PDV2).
        Escreve nas colunas corretas: Suprimento_Cofre ou Retirada_Cofre.
        Fallback: 'Fechamento_PDV_Lancamentos' (sem warnings).
        """
        ws_name = "Fechamentos_PDV1" if pdv_code == "PDV 1" else "Fechamentos_PDV2"

        try:
            dados = buscar_dados(spreadsheet, ws_name) or []
        except Exception:
            dados = None

        if dados:
            df = pd.DataFrame(dados)
            if not df.empty:
                cols = list(df.columns)
                low  = {c: c.lower() for c in cols}

                col_data = next((c for c in cols if "data" in low[c]), None)
                col_pdv  = next((c for c in cols if "pdv"  in low[c]), None)

                # coluna alvo correta
                if tipo_mov_pdv == "Suprimento":
                    target = "Suprimento_Cofre" if "Suprimento_Cofre" in cols else \
                             next((c for c in cols if "supr" in low[c] and "cofre" in low[c]), None)
                else:  # "Sangria"
                    target = "Retirada_Cofre" if "Retirada_Cofre" in cols else \
                             next((c for c in cols if "retirada" in low[c] and "cofre" in low[c]), None)

                if col_data and col_pdv and target:
                    ws = get_or_create_worksheet(spreadsheet, ws_name, cols)
                    nova = {c: "" for c in cols}
                    nova[col_data] = str(data_mov)
                    nova[col_pdv]  = pdv_code
                    nova[target]   = float(valor)

                    col_vinc = next((c for c in cols if "vinculo" in low[c]), None)
                    if col_vinc: nova[col_vinc] = vinculo_id
                    col_obs  = next((c for c in cols if "observ" in low[c]), None)
                    if col_obs:  nova[col_obs]  = f"Gerado via Cofre ({tipo_mov_pdv}). {obs or ''}"

                    ws.append_row([nova.get(c, "") for c in cols])
                    return True

        # Fallback silencioso (auditoria)
        ws_fb = get_or_create_worksheet(
            spreadsheet,
            "Fechamento_PDV_Lancamentos",
            ["Data","PDV","Tipo","Valor","Vinculo_ID","Observacoes"]
        )
        ws_fb.append_row([
            str(data_mov), pdv_code, tipo_mov_pdv,
            float(valor), vinculo_id, f"Gerado via Cofre. {obs or ''}"
        ])
        return False

    # ---- Saldo do Cofre ----
    try:
        cofre_data = buscar_dados(spreadsheet, ABA_COFRE) or []
        df_cofre = pd.DataFrame(cofre_data)

        saldo_cofre = Decimal("0")
        entradas = Decimal("0")
        saidas   = Decimal("0")

        if not df_cofre.empty and "Valor" in df_cofre.columns:
            df_cofre["Valor"] = pd.to_numeric(df_cofre["Valor"], errors="coerce").fillna(0.0)
            if "Tipo" in df_cofre.columns:
                t = df_cofre["Tipo"].astype(str).str.lower()
                entradas = Decimal(str(df_cofre.loc[t.eq("entrada"), "Valor"].sum()))
                saidas   = Decimal(str(df_cofre.loc[t.isin(["saída","saida"]), "Valor"].sum()))
            saldo_cofre = entradas - saidas

        # Ajuste: PDV sem vínculo (não duplicar os que já tem Vinculo_ID no cofre)
        try:
            mov_pdv = buscar_dados(spreadsheet, ABA_MOV_PDV) or []
            df_pdv = pd.DataFrame(mov_pdv)
            if not df_pdv.empty and {"Valor","Tipo_Mov"}.issubset(df_pdv.columns):
                df_pdv["Valor"] = pd.to_numeric(df_pdv["Valor"], errors="coerce").fillna(0.0)
                cofre_vinc = set(df_cofre["Vinculo_ID"].astype(str)) if (not df_cofre.empty and "Vinculo_ID" in df_cofre.columns) else set()
                if "Vinculo_ID" in df_pdv.columns:
                    df_pdv = df_pdv[~df_pdv["Vinculo_ID"].astype(str).isin(cofre_vinc)]
                supr = df_pdv.loc[df_pdv["Tipo_Mov"].astype(str).str.lower().eq("suprimento"), "Valor"].sum()
                sang = df_pdv.loc[df_pdv["Tipo_Mov"].astype(str).str.lower().eq("sangria"), "Valor"].sum()
                saldo_cofre += Decimal(str(sang)) - Decimal(str(supr))
        except Exception:
            pass

        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg,#FFD700 0%,#FFA500 100%);padding:14px;border-radius:14px;text-align:center">
              <div style="font-size:28px;font-weight:700;">R$ {saldo_cofre:,.2f}</div>
              <div>🔒 Saldo Atual do Cofre</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("---")
    except Exception as e:
        st.error(f"❌ Erro ao calcular saldo do cofre: {e}")

    # ---- Abas da interface ----
    tab1, tab2 = st.tabs(["➕ Registrar Movimentação", "📋 Histórico do Cofre"])

    # =========================
    # TAB 1 — Registrar
    # =========================
    with tab1:
        st.markdown("#### Nova Movimentação no Cofre")
        data_mov = st.date_input("Data da Movimentação", value=_date.today(), key="cofre_data_mov")
        tipo_mov = st.selectbox("Tipo de Movimentação", ["Entrada", "Saída"], key="cofre_tipo_mov")

        with st.form("form_mov_cofre", clear_on_submit=True):
            valor = st.number_input("Valor da Movimentação (R$)", min_value=0.01, step=0.01, format="%.2f", key="cofre_valor")
            categoria, origem, destino = "", "", ""
            obs_user = ""

            if tipo_mov == "Saída":
                # >>> NOVO: adicionada a opção "Depósito Banco"
                tipo_saida = st.selectbox(
                    "Tipo de Saída",
                    ["Para PDV (Caixa Lotérica)", "Para Caixa Interno", "Pagamento de Despesa", "Depósito Banco", "Outros"],
                    key="cofre_tipo_saida"
                )

                # PDV só aparece quando a saída for para PDV (Lotérica)
                if tipo_saida == "Para PDV (Caixa Lotérica)":
                    pdv_ui = st.selectbox("Transferir para (PDV)", PDV_UI_LIST, key="cofre_destino_pdv")
                    pdv_code = PDV_UI_TO_CODE[pdv_ui]
                    categoria = "Transferência para Caixa Lotérica"
                    origem = "Cofre Principal"
                    destino = f"Caixa Lotérica - {pdv_code}"

                elif tipo_saida == "Para Caixa Interno":
                    categoria = "Transferência para Caixa Interno"
                    origem = "Cofre Principal"
                    destino = "Caixa Interno"

                elif tipo_saida == "Pagamento de Despesa":
                    categoria = "Pagamento de Despesa"
                    origem = "Cofre Principal"
                    destino = st.text_input("Descrição da Despesa (Ex.: Aluguel, Fornecedor X)", key="cofre_desc_desp")

                elif tipo_saida == "Depósito Banco":  # <<< NOVO
                    categoria = "Depósito Banco"
                    origem = "Cofre Principal"
                    destino = "Banco"
                    # campo opcional para detalhar o depósito (não mostra PDV)
                    detalhes_banco = st.text_input("Banco / Agência / Conta / Comprovante (opcional)", key="cofre_det_banco")

                else:
                    categoria = "Outros"
                    origem = "Cofre Principal"
                    destino = st.text_input("Destino (descrição livre)", key="cofre_destino_outros_saida")

            else:  # Entrada
                origem_entrada = st.selectbox(
                    "Origem da Entrada",
                    ["Banco", "Sócio", "Vendas", "Sangria dos PDVs", "Outros"],
                    key="cofre_cat_entrada"
                )
                if origem_entrada == "Sangria dos PDVs":
                    pdv_ui_in = st.selectbox("Selecione o PDV (origem da sangria)", PDV_UI_LIST, key="cofre_pdv_ui_entrada")
                    pdv_code_in = PDV_UI_TO_CODE[pdv_ui_in]
                    categoria = "Sangria dos PDVs"
                    origem = pdv_code_in
                    destino = "Cofre Principal"
                elif origem_entrada == "Outros":
                    categoria = "Outros"
                    origem = st.text_input("Detalhe da Origem", key="cofre_origem_outros_entrada")
                    destino = "Cofre Principal"
                else:
                    categoria = origem_entrada
                    origem = origem_entrada
                    destino = "Cofre Principal"

            obs_user = st.text_area("Observações", key="cofre_obs")

            if st.form_submit_button("💾 Salvar Movimentação", use_container_width=True):
                if float(valor) <= 0:
                    st.warning("Informe um valor maior que zero.")
                else:
                    try:
                        # 1) Registra no COFRE
                        ws_cofre = get_or_create_worksheet(spreadsheet, ABA_COFRE, HEADERS_COFRE)
                        vinculo_id = _gerar_id("COFRE")
                        hora_agora = obter_horario_brasilia()

                        # Complementa observação quando for Depósito Banco
                        obs_final = f"Vínculo: {vinculo_id}. {obs_user or ''}"
                        if (tipo_mov == "Saída") and (categoria == "Depósito Banco"):
                            try:
                                if detalhes_banco:
                                    obs_final = f"{obs_final} Banco: {detalhes_banco}."
                            except NameError:
                                pass  # se o campo não existir por alguma razão

                        ws_cofre.append_row([
                            str(data_mov), str(hora_agora), st.session_state.get("nome_usuario",""),
                            tipo_mov, categoria, origem, destino, float(valor),
                            obs_final, "Concluído", vinculo_id
                        ])

                        # 2) Integrações automáticas
                        # 2.1) Saída -> Caixa Interno  => Suprimento no Operacoes_Caixa
                        if (tipo_mov == "Saída") and (destino == "Caixa Interno"):
                            ws_caixa = get_or_create_worksheet(spreadsheet, ABA_CAIXA_INTERNO, HEADERS_CAIXA)
                            ws_caixa.append_row([
                                str(data_mov), str(hora_agora), st.session_state.get("nome_usuario",""),
                                "Suprimento", "Sistema", "N/A",
                                float(valor), 0.0, 0.0, float(valor), 0.0,
                                "Concluído", "", "0.00%",
                                f"Transferência do Cofre → Caixa Interno. Vínculo {vinculo_id}."
                            ])

                        # 2.2) Saída -> PDV (Caixa Lotérica) => PDV: Suprimento + Fechamento: Suprimento_Cofre
                        if (tipo_mov == "Saída") and isinstance(destino, str) and destino.startswith("Caixa Lotérica - "):
                            pdv_code = "PDV 1" if "PDV 1" in destino else "PDV 2"
                            ws_mov_pdv = get_or_create_worksheet(spreadsheet, ABA_MOV_PDV, HEADERS_MOV_PDV)

                            mov_exist = buscar_dados(spreadsheet, ABA_MOV_PDV) or []
                            df_mov = pd.DataFrame(mov_exist)
                            ja_existe = (not df_mov.empty and "Vinculo_ID" in df_mov.columns
                                         and df_mov["Vinculo_ID"].astype(str).eq(vinculo_id).any())
                            if not ja_existe:
                                ws_mov_pdv.append_row([
                                    str(data_mov), str(hora_agora),
                                    pdv_code, "Suprimento",
                                    float(valor), vinculo_id, st.session_state.get("nome_usuario",""),
                                    f"Cofre → {pdv_code}. {obs_user or ''}"
                                ])
                            _try_registrar_no_fechamento_pdv(data_mov, pdv_code, "Suprimento", valor, vinculo_id, obs_user)

                        # 2.3) Entrada (Sangria dos PDVs) => PDV: Sangria + Fechamento: Retirada_Cofre
                        if (tipo_mov == "Entrada") and (categoria == "Sangria dos PDVs") and (origem in ["PDV 1","PDV 2"]):
                            ws_mov_pdv = get_or_create_worksheet(spreadsheet, ABA_MOV_PDV, HEADERS_MOV_PDV)
                            mov_exist = buscar_dados(spreadsheet, ABA_MOV_PDV) or []
                            df_mov = pd.DataFrame(mov_exist)
                            ja_existe = (not df_mov.empty and "Vinculo_ID" in df_mov.columns
                                         and df_mov["Vinculo_ID"].astype(str).eq(vinculo_id).any())
                            if not ja_existe:
                                ws_mov_pdv.append_row([
                                    str(data_mov), str(hora_agora),
                                    origem, "Sangria",
                                    float(valor), vinculo_id, st.session_state.get("nome_usuario",""),
                                    f"{origem} → Cofre. {obs_user or ''}"
                                ])
                            _try_registrar_no_fechamento_pdv(data_mov, origem, "Sangria", valor, vinculo_id, obs_user)

                        st.success(f"✅ Movimentação de R$ {valor:,.2f} registrada, integrada ao PDV e refletida no Fechamento.")
                        st.cache_data.clear()

                    except Exception as e:
                        st.error(f"❌ Erro ao salvar movimentação: {e}")

    # =========================
    # TAB 2 — Histórico
    # =========================
    with tab2:
        st.markdown("#### Histórico de Movimentações")
        try:
            cofre_hist = buscar_dados(spreadsheet, ABA_COFRE) or []
            dfh = pd.DataFrame(cofre_hist)
            if not dfh.empty:
                if "Data" in dfh.columns:
                    try: dfh["Data"] = pd.to_datetime(dfh["Data"], errors="coerce")
                    except Exception: pass
                sort_cols = [c for c in ["Data","Hora"] if c in dfh.columns]
                if sort_cols:
                    dfh = dfh.sort_values(by=sort_cols, ascending=False)
                st.dataframe(dfh, use_container_width=True)
            else:
                st.info("Nenhuma movimentação registrada no cofre.")
        except Exception:
            st.info("Nenhuma movimentação registrada no cofre.")





# Fechamento Diário do Caixa Interno (robusto)
# Fechamento Diário do Caixa Interno (mantém formato original e recalcula no salvar)
def render_fechamento_diario_simplificado(spreadsheet):
    st.subheader("🗓️ Fechamento Diário do Caixa Interno")

    # Configurações/base
    TIPOS_SAQUE  = ["Saque Cartão Débito", "Saque Cartão Crédito"]
    TIPOS_CHEQUE = ["Cheque à Vista", "Cheque Pré-datado", "Cheque com Taxa Manual"]

    try:
        HEADERS_FECHAMENTO_CAIXA = [
            "Data_Fechamento", "Operador", "Saldo_Dia_Anterior",
            "Total_Saques_Cartao", "Total_Trocas_Cheque", "Total_Suprimentos",
            "Saldo_Calculado_Dia", "Dinheiro_Contado_Gaveta", "Diferenca_Caixa",
            "Observacoes_Fechamento"
        ]

        # -------- helper: carrega operações do dia e calcula totais (formatação original) --------
        def _calcular_totais_dia(data_ref, saldo_anterior):
            operacoes_data = buscar_dados(spreadsheet, "Operacoes_Caixa") or []
            if operacoes_data:
                df_op = pd.DataFrame(normalizar_dados_inteligente(operacoes_data))
                # tipagem (mantém seu to_numeric direto)
                for c in ["Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro"]:
                    if c in df_op.columns:
                        df_op[c] = pd.to_numeric(df_op[c], errors="coerce").fillna(0.0)
                try:
                    df_op["Data"] = pd.to_datetime(df_op["Data"], errors="coerce").dt.date
                except Exception:
                    pass
                df_op.dropna(subset=["Data"], inplace=True)
                operacoes_do_dia = df_op[df_op["Data"] == data_ref]
            else:
                operacoes_do_dia = pd.DataFrame()

            total_saques_cartao = operacoes_do_dia[operacoes_do_dia["Tipo_Operacao"].isin(TIPOS_SAQUE)]["Valor_Liquido"].sum() if not operacoes_do_dia.empty else 0.0
            total_trocas_cheque = operacoes_do_dia[operacoes_do_dia["Tipo_Operacao"].isin(TIPOS_CHEQUE)]["Valor_Liquido"].sum() if not operacoes_do_dia.empty else 0.0
            total_suprimentos   = operacoes_do_dia[operacoes_do_dia["Tipo_Operacao"] == "Suprimento"]["Valor_Bruto"].sum() if not operacoes_do_dia.empty else 0.0

            saldo_calculado_dia = float(saldo_anterior + total_suprimentos - (total_saques_cartao + total_trocas_cheque))
            return float(total_saques_cartao), float(total_trocas_cheque), float(total_suprimentos), float(saldo_calculado_dia), operacoes_do_dia

        # ---------------- 1) Escolher a DATA do fechamento ----------------
        hoje_sys = obter_date_brasilia()
        st.markdown("Selecione a data para calcular e registrar o fechamento (pode ser dias anteriores).")
        data_alvo = st.date_input("Data do Fechamento", value=hoje_sys, key="dt_fechamento_alvo")

        if data_alvo > hoje_sys:
            st.error("❌ Não é possível fechar uma data futura.")
            return

        dia_anterior = data_alvo - timedelta(days=1)

        # ---------------- 2) Buscar SALDO do dia anterior ----------------
        saldo_dia_anterior = 0.0
        usou_zero = True
        try:
            fechamentos_data = buscar_dados(spreadsheet, "Fechamento_Diario_Caixa_Interno") or []
            df_fech = pd.DataFrame(fechamentos_data)
            if not df_fech.empty:
                df_fech["Data_Fechamento"] = pd.to_datetime(df_fech["Data_Fechamento"], errors="coerce").dt.date
                df_fech["Saldo_Calculado_Dia"] = pd.to_numeric(df_fech.get("Saldo_Calculado_Dia", 0), errors="coerce").fillna(0.0)
                # último fechamento <= dia_anterior
                prev = df_fech[df_fech["Data_Fechamento"] <= dia_anterior].sort_values("Data_Fechamento").tail(1)
                if not prev.empty:
                    saldo_dia_anterior = float(prev.iloc[0]["Saldo_Calculado_Dia"])
                    usou_zero = False
        except Exception as e:
            st.warning(f"⚠️ Erro ao buscar saldos anteriores: {e}")

        msg = f"**Saldo final do último fechamento ≤ {dia_anterior.strftime('%d/%m/%Y')}:** R$ {saldo_dia_anterior:,.2f}"
        if usou_zero:
            msg += "  \n_(nenhum fechamento anterior encontrado; assumindo R$ 0,00)_"
        st.markdown(msg)
        st.markdown("---")

        # ---------------- 3) Totais do DIA-ALVO (preview) ----------------
        total_saques_cartao, total_trocas_cheque, total_suprimentos, saldo_calculado_dia, operacoes_do_dia = \
            _calcular_totais_dia(data_alvo, saldo_dia_anterior)

        # Alerta operacional (só para a data alvo)
        tem_mov = len(operacoes_do_dia) > 0
        tem_supr = False if operacoes_do_dia.empty else len(operacoes_do_dia[operacoes_do_dia["Tipo_Operacao"] == "Suprimento"]) > 0
        if tem_mov and not tem_supr:
            st.markdown("""
            <div style="background:#fff3cd;color:#856404;border:1px solid #ffeeba;padding:10px;border-radius:10px;">
                ⚠️ <b>Atenção:</b> Há movimentações nesta data, mas <u>nenhum Suprimento foi registrado</u>.
                Isso pode distorcer o saldo e os relatórios.
            </div>
            """, unsafe_allow_html=True)

        # ---------------- 4) Resumo visual ----------------
        st.markdown("#### Resumo do Dia Selecionado")
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Total Saques Cartão", f"R$ {total_saques_cartao:,.2f}")
        with c2: st.metric("Total Trocas Cheque", f"R$ {total_trocas_cheque:,.2f}")
        with c3: st.metric("Total Suprimentos", f"R$ {total_suprimentos:,.2f}")

        st.markdown(f"**Saldo Calculado ({data_alvo.strftime('%d/%m/%Y')}):** R$ {saldo_calculado_dia:,.2f}")
        st.markdown("---")

        # ---------------- 5) Registrar/Alterar fechamento ----------------
        with st.form("form_fechamento_caixa_simplificado", clear_on_submit=True):
            st.markdown("#### Registrar/Editar Fechamento")
            dinheiro_contado = st.number_input("Dinheiro Contado na Gaveta (R$)", min_value=0.0, step=10.0, format="%.2f", key="din_cont_fech")
            observacoes_fech = st.text_area("Observações do Fechamento (Opcional)", key="obs_fech")

            diferenca_preview = float(dinheiro_contado - saldo_calculado_dia)
            st.markdown(f"**Diferença:** R$ {diferenca_preview:,.2f}")

            # Se já existir fechamento na data-alvo, permitir sobrescrever (opcional)
            existe_registro_alvo = False
            row_alvo = None
            try:
                if not df_fech.empty:
                    df_exist = df_fech[df_fech["Data_Fechamento"] == data_alvo]
                    if not df_exist.empty:
                        existe_registro_alvo = True
                        idx = df_exist.index[0]
                        row_alvo = idx + 2  # 1-based + cabeçalho
            except Exception:
                pass

            col_b1, col_b2 = st.columns([1,1])
            with col_b1:
                btn_salvar = st.form_submit_button("💾 Salvar Fechamento", use_container_width=True)
            with col_b2:
                sobrescrever = st.checkbox("Sobrescrever se já existir", value=False) if existe_registro_alvo else False

        if 'btn_salvar' in locals() and btn_salvar:
            try:
                if "nome_usuario" not in st.session_state:
                    st.session_state.nome_usuario = "OPERADOR"

                # >>> Recalcula neste instante (lendo Operacoes_Caixa) para gravar números corretos
                ts, tc, sup, saldo_calc, _ = _calcular_totais_dia(data_alvo, saldo_dia_anterior)
                diferenca = float(dinheiro_contado - saldo_calc)

                ws = get_or_create_worksheet(spreadsheet, "Fechamento_Diario_Caixa_Interno", HEADERS_FECHAMENTO_CAIXA)
                linha = [
                    str(data_alvo),
                    st.session_state.nome_usuario,
                    float(saldo_dia_anterior),
                    float(ts),
                    float(tc),
                    float(sup),
                    float(saldo_calc),
                    float(dinheiro_contado),
                    float(diferenca),
                    observacoes_fech
                ]

                if existe_registro_alvo and sobrescrever and row_alvo:
                    ws.update(f"A{row_alvo}:J{row_alvo}", [linha])
                    st.success(f"✅ Fechamento de {data_alvo.strftime('%d/%m/%Y')} atualizado com sucesso!")
                elif existe_registro_alvo and not sobrescrever:
                    st.error("❌ Já existe fechamento para essa data. Marque 'Sobrescrever' para atualizar.")
                    return
                else:
                    ws.append_row(linha)
                    st.success(f"✅ Fechamento de {data_alvo.strftime('%d/%m/%Y')} registrado com sucesso!")

                st.cache_data.clear()
            except Exception as e:
                st.error(f"❌ Erro ao salvar fechamento: {e}")

        # ---------------- 6) Expander de conferência ----------------
        with st.expander("🔍 Conferência rápida dessa data"):
            st.write(f"Linhas de {data_alvo}: {len(operacoes_do_dia)}")
            if not operacoes_do_dia.empty:
                st.dataframe(
                    operacoes_do_dia.groupby("Tipo_Operacao", as_index=False)[
                        ["Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro"]
                    ].sum().sort_values("Valor_Liquido", ascending=False),
                    use_container_width=True
                )

    except Exception as e:
        st.error(f"❌ Erro ao carregar fechamento de caixa: {str(e)}")
        st.info("🔄 Tente recarregar a página ou verifique a conexão com o Google Sheets.")




# ------------------------------------------------------------
# 🛠️ Gestão do Caixa Interno — Fechamentos (Histórico + Edição)
# ------------------------------------------------------------
def render_gestao_caixa_interno(spreadsheet):
    st.subheader("🛠️ Gestão do Caixa Interno — Fechamentos")

    SHEET = "Fechamento_Diario_Caixa_Interno"
    HEADERS = [
        "Data_Fechamento", "Operador", "Saldo_Dia_Anterior",
        "Total_Saques_Cartao", "Total_Trocas_Cheque", "Total_Suprimentos",
        "Saldo_Calculado_Dia", "Dinheiro_Contado_Gaveta", "Diferenca_Caixa",
        "Observacoes_Fechamento"
    ]

    # garante a planilha
    ws = get_or_create_worksheet(spreadsheet, SHEET, HEADERS)

    # util: carregar DF com índice real da linha (_row) para editar/remover
    def _load_df():
        values = ws.get_all_values()
        if not values or len(values) < 2:
            return pd.DataFrame(columns=HEADERS + ["_row"])

        hdr = values[0]
        rows = values[1:]
        df = pd.DataFrame(rows, columns=hdr)
        df["_row"] = list(range(2, 2 + len(df)))  # linha real na planilha (1 = cabeçalho)

        # normalização
        df["Data_Fechamento"] = pd.to_datetime(df["Data_Fechamento"], errors="coerce").dt.date
        for c in ["Saldo_Dia_Anterior","Total_Saques_Cartao","Total_Trocas_Cheque",
                  "Total_Suprimentos","Saldo_Calculado_Dia","Dinheiro_Contado_Gaveta",
                  "Diferenca_Caixa"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
        return df

    tab_hist, tab_edit = st.tabs(["📜 Histórico", "✏️ Editar / Remover"])

    # -------------------- HISTÓRICO --------------------
    with tab_hist:
        df = _load_df()
        if df.empty:
            st.info("Nenhum fechamento registrado ainda.")
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                modo = st.radio("Filtro", ["Por dia", "Período"], horizontal=True, key="flt_gci_modo")
            with c2:
                if modo == "Por dia":
                    dia = st.date_input("Data", value=df["Data_Fechamento"].max(), key="flt_gci_dia")
                else:
                    ini = st.date_input("Início", value=df["Data_Fechamento"].min(), key="flt_gci_ini")
            with c3:
                if modo == "Período":
                    fim = st.date_input("Fim", value=df["Data_Fechamento"].max(), key="flt_gci_fim")

            if modo == "Por dia":
                df_f = df[df["Data_Fechamento"] == (dia or df["Data_Fechamento"].max())]
            else:
                df_f = df[(df["Data_Fechamento"] >= ini) & (df["Data_Fechamento"] <= fim)]

            if df_f.empty:
                st.info("Sem registros no filtro selecionado.")
            else:
                # KPIs
                k1, k2, k3, k4 = st.columns(4)
                with k1: st.metric("Fechamentos", len(df_f))
                with k2: st.metric("Saques (Σ)", f"R$ {df_f['Total_Saques_Cartao'].sum():,.2f}")
                with k3: st.metric("Cheques (Σ)", f"R$ {df_f['Total_Trocas_Cheque'].sum():,.2f}")
                with k4: st.metric("Suprimentos (Σ)", f"R$ {df_f['Total_Suprimentos'].sum():,.2f}")

                st.markdown("#### Registros")
                cols_show = [
                    "Data_Fechamento","Operador","Saldo_Dia_Anterior",
                    "Total_Saques_Cartao","Total_Trocas_Cheque","Total_Suprimentos",
                    "Saldo_Calculado_Dia","Dinheiro_Contado_Gaveta","Diferenca_Caixa",
                    "Observacoes_Fechamento"
                ]
                st.dataframe(
                    df_f.sort_values(["Data_Fechamento","Operador"], ascending=[False, True])[cols_show],
                    use_container_width=True
                )

    # ----------------- EDITAR / REMOVER ----------------
    with tab_edit:
        df = _load_df()
        if df.empty:
            st.info("Nenhum fechamento para editar/remover.")
            return

        df_sorted = df.sort_values("Data_Fechamento", ascending=False).copy()
        df_sorted["label"] = df_sorted.apply(
            lambda r: f"{r['Data_Fechamento']} | {r['Operador']} | Saldo: R$ {r['Saldo_Calculado_Dia']:,.2f} (linha {r['_row']})",
            axis=1
        )
        mapa_row = {r["label"]: int(r["_row"]) for _, r in df_sorted.iterrows()}
        escolha = st.selectbox("Selecione o registro", list(mapa_row.keys()))
        if not escolha:
            st.stop()

        row_idx = mapa_row[escolha]
        reg = df[df["_row"] == row_idx].iloc[0]

        # aviso de duplicidade por data
        dup = df[(df["Data_Fechamento"] == reg["Data_Fechamento"]) & (df["_row"] != row_idx)]
        if not dup.empty:
            st.warning(f"⚠️ Existem {len(dup)} outro(s) registro(s) na mesma data ({reg['Data_Fechamento']}).")

        # variáveis de controle dos botões (para existirem fora do form)
        salvar = False
        remover = False
        confirma_del = False

        st.markdown("#### Editar registro")
        with st.form("form_edit_fechamento", clear_on_submit=False):
            data_edt = st.date_input("Data do Fechamento", value=reg["Data_Fechamento"])
            operador = st.text_input("Operador", value=str(reg["Operador"]))

            c1, c2, c3 = st.columns(3)
            with c1:
                saldo_ant = st.number_input("Saldo do Dia Anterior (R$)", value=float(reg["Saldo_Dia_Anterior"]),
                                            step=10.0, format="%.2f")
            with c2:
                saques = st.number_input("Total Saques Cartão (R$)", value=float(reg["Total_Saques_Cartao"]),
                                         step=10.0, format="%.2f")
            with c3:
                cheques = st.number_input("Total Trocas Cheque (R$)", value=float(reg["Total_Trocas_Cheque"]),
                                          step=10.0, format="%.2f")

            c4, c5, c6 = st.columns(3)
            with c4:
                supr = st.number_input("Total Suprimentos (R$)", value=float(reg["Total_Suprimentos"]),
                                       step=10.0, format="%.2f")
            with c5:
                saldo_calc = st.number_input("Saldo Calculado do Dia (R$)",
                                             value=float(reg["Saldo_Calculado_Dia"]), step=10.0, format="%.2f")
            with c6:
                dinheiro = st.number_input("Dinheiro Contado na Gaveta (R$)",
                                           value=float(reg["Dinheiro_Contado_Gaveta"]), step=10.0, format="%.2f")

            diferenca = float(dinheiro) - float(saldo_calc)
            st.info(f"🔎 Diferença recalculada: R$ {diferenca:,.2f}")

            obs = st.text_area("Observações do Fechamento", value=str(reg.get("Observacoes_Fechamento", "")))

            col_btn1, col_btn2, _ = st.columns([1, 1, 2])
            salvar  = col_btn1.form_submit_button("💾 Salvar alterações", use_container_width=True)

            # ATENÇÃO: dentro do form, use form_submit_button (nunca st.button)
            with col_btn2:
                confirma_del = st.checkbox("Confirmar exclusão")
                remover = st.form_submit_button(
                    "🗑️ Remover registro",
                    use_container_width=True,
                    disabled=not confirma_del
                )

        # ---- ações pós-submit (fora do form) ----
        if salvar:
            try:
                # monta a linha no exato order dos HEADERS
                linha = [
                    str(data_edt),
                    operador,
                    float(saldo_ant),
                    float(saques),
                    float(cheques),
                    float(supr),
                    float(saldo_calc),
                    float(dinheiro),
                    float(diferenca),
                    obs
                ]
                ws.update(f"A{row_idx}:J{row_idx}", [linha])
                st.success("✅ Registro atualizado com sucesso!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"❌ Erro ao atualizar: {e}")

        if remover and confirma_del:
            try:
                ws.delete_rows(row_idx)
                st.success("🗑️ Registro removido com sucesso!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"❌ Erro ao remover: {e}")


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

        # Menu por perfil
        if st.session_state.tipo_usuario == "👑 Gerente":
            st.title("👑 Dashboard Gerencial - Sistema Unificado")
            opcoes_menu = {
                "📊 Dashboard Caixa": "dashboard_caixa",
                "💳 Operações Caixa": "operacoes_caixa",
                "🏦 Gestão do Cofre": "cofre",
                "📋 Fechamento Lotérica": "fechamento_loterica",
                "🗓️ Fechamento Caixa Interno": "fechamento_diario_caixa_interno",
                "🛠️ Gestão Caixa Interno": "gestao_caixa_interno",
                "📈 Gestão Lotérica": "gestao_loterica",
            }
        elif st.session_state.tipo_usuario == "💳 Operador Caixa":
            st.title("💳 Sistema Caixa Interno")
            opcoes_menu = {
                "📊 Dashboard Caixa": "dashboard_caixa",
                "💳 Operações Caixa": "operacoes_caixa",
                "🗓️ Fechamento Caixa Interno": "fechamento_diario_caixa_interno",
            }
        else:  # Operador Lotérica
            st.title("🎰 Sistema Lotérica")
            opcoes_menu = {"📋 Fechamento Lotérica": "fechamento_loterica"}

                # Navegação
        if "pagina_atual" not in st.session_state:
            st.session_state.pagina_atual = list(opcoes_menu.values())[0]

        for i, (nome_opcao, chave_opcao) in enumerate(opcoes_menu.items()):
            if st.sidebar.button(nome_opcao, key=f"nav_{i}_{chave_opcao}", use_container_width=True):
                st.session_state.pagina_atual = chave_opcao
                st.rerun()

        st.sidebar.markdown("---")
        if st.sidebar.button("🚪 Sair do Sistema", key="btn_sair", use_container_width=True):
            # limpa tudo e encerra o ciclo atual imediatamente
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
            st.stop()

        # Dispatcher único (lazy): resolve por NOME e só chama se existir
        def _render_page(page_key: str):
            name_map = {
                "dashboard_caixa": "render_dashboard_caixa",
                "operacoes_caixa": "render_operacoes_caixa",
                "cofre": "render_cofre",
                "fechamento_loterica": "render_fechamento_loterica",
                "fechamento_diario_caixa_interno": "render_fechamento_diario_simplificado",
                "gestao_caixa_interno": "render_gestao_caixa_interno",
                "gestao_loterica": "render_gestao_loterica", 
            }
            fn_name = name_map.get(page_key, "render_dashboard_caixa")
            fn = globals().get(fn_name)
            if fn is None:
                st.error(f"⚠️ Página '{page_key}' inválida (função '{fn_name}' não encontrada).")
                return
            return fn(spreadsheet)

        _render_page(st.session_state.pagina_atual)
    except Exception as e:
        st.error(f"❌ Erro durante execução: {e}")


if __name__ == "__main__":
    main()
