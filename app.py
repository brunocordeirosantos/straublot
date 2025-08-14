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
# Fechamento de Caixa da Lotérica (PDV1/PDV2)
# ------------------------------------------------------------
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

            c1, c2 = st.columns(2)
            with c1:
                pdv_selecionado = st.selectbox("Selecione o PDV", ["PDV 1", "PDV 2"], key="pdv_sel_fech")
            with c2:
                data_fechamento = st.date_input("Data do Fechamento", value=obter_date_brasilia(), key="data_fech_lot")

            # ---- Nome real da planilha (corrige o espaço) ----
            pdv_to_sheet = {"PDV 1": "Fechamentos_PDV1", "PDV 2": "Fechamentos_PDV2"}
            sheet_name = pdv_to_sheet.get(pdv_selecionado, "Fechamentos_PDV1")

            # ---- Buscar saldo do dia anterior com tolerância ----
            saldo_anterior = 0.0
            data_anterior = data_fechamento - timedelta(days=1)
            try:
                fechamentos_data = buscar_dados(spreadsheet, sheet_name)
                df_fech = pd.DataFrame(fechamentos_data)

                if not df_fech.empty:
                    df_fech["Data_Fechamento"] = pd.to_datetime(df_fech["Data_Fechamento"], errors="coerce").dt.date
                    df_fech["Saldo_Final_Calculado"] = pd.to_numeric(df_fech["Saldo_Final_Calculado"], errors="coerce").fillna(0.0)

                    # 1) tenta o registro exatamente do dia anterior
                    reg = df_fech[df_fech["Data_Fechamento"] == data_anterior]
                    # 2) senão, pega o último antes da data do fechamento
                    if reg.empty:
                        prev = df_fech[df_fech["Data_Fechamento"] < data_fechamento]
                        if not prev.empty:
                            reg = prev.sort_values("Data_Fechamento").tail(1)
                    if not reg.empty:
                        saldo_anterior = float(reg.iloc[0]["Saldo_Final_Calculado"])
            except Exception as e:
                st.warning(f"⚠️ Erro ao buscar dados de {sheet_name}: {e}")

            st.info(f"💰 Saldo anterior ({data_anterior.strftime('%d/%m/%Y')}): R$ {saldo_anterior:,.2f}")

            # ===================== COMPRAS ======================
            st.markdown("### 🛒 Compras do Dia")
            cc1, cc2, cc3 = st.columns(3)

            with cc1:
                st.markdown("**Bolão**")
                qtd_comp_bolao = st.number_input("Quantidade", min_value=0, step=1, key="qtd_comp_bolao")
                custo_unit_bolao = st.number_input("Custo Unitário (R$)", min_value=0.0, step=0.01, format="%.2f", key="custo_bolao")
                total_comp_bolao = float(qtd_comp_bolao) * float(custo_unit_bolao)
                st.write(f"Total: R$ {total_comp_bolao:,.2f}")

            with cc2:
                st.markdown("**Raspadinha**")
                qtd_comp_rasp = st.number_input("Quantidade", min_value=0, step=1, key="qtd_comp_rasp")
                custo_unit_rasp = st.number_input("Custo Unitário (R$)", min_value=0.0, step=0.01, format="%.2f", key="custo_rasp")
                total_comp_rasp = float(qtd_comp_rasp) * float(custo_unit_rasp)
                st.write(f"Total: R$ {total_comp_rasp:,.2f}")

            with cc3:
                st.markdown("**Loteria Federal**")
                qtd_comp_fed = st.number_input("Quantidade", min_value=0, step=1, key="qtd_comp_fed")
                custo_unit_fed = st.number_input("Custo Unitário (R$)", min_value=0.0, step=0.01, format="%.2f", key="custo_fed")
                total_comp_fed = float(qtd_comp_fed) * float(custo_unit_fed)
                st.write(f"Total: R$ {total_comp_fed:,.2f}")

            # ===================== VENDAS =======================
            st.markdown("### 💰 Vendas do Dia")
            cv1, cv2, cv3 = st.columns(3)

            with cv1:
                st.markdown("**Bolão**")
                qtd_vend_bolao = st.number_input("Quantidade", min_value=0, step=1, key="qtd_vend_bolao")
                preco_unit_bolao = st.number_input("Preço Unitário (R$)", min_value=0.0, step=0.01, format="%.2f", key="preco_bolao")
                total_vend_bolao = float(qtd_vend_bolao) * float(preco_unit_bolao)
                st.write(f"Total: R$ {total_vend_bolao:,.2f}")

            with cv2:
                st.markdown("**Raspadinha**")
                qtd_vend_rasp = st.number_input("Quantidade", min_value=0, step=1, key="qtd_vend_rasp")
                preco_unit_rasp = st.number_input("Preço Unitário (R$)", min_value=0.0, step=0.01, format="%.2f", key="preco_rasp")
                total_vend_rasp = float(qtd_vend_rasp) * float(preco_unit_rasp)
                st.write(f"Total: R$ {total_vend_rasp:,.2f}")

            with cv3:
                st.markdown("**Loteria Federal**")
                qtd_vend_fed = st.number_input("Quantidade", min_value=0, step=1, key="qtd_vend_fed")
                preco_unit_fed = st.number_input("Preço Unitário (R$)", min_value=0.0, step=0.01, format="%.2f", key="preco_fed")
                total_vend_fed = float(qtd_vend_fed) * float(preco_unit_fed)
                st.write(f"Total: R$ {total_vend_fed:,.2f}")

            # ================== OUTRAS MOVIMENTAÇÕES ==================
            st.markdown("### 🔄 Outras Movimentações")
            mo1, mo2 = st.columns(2)
            with mo1:
                movimentacao_cielo   = st.number_input("Movimentação Cielo (R$)",   min_value=0.0, step=0.01, format="%.2f", key="mov_cielo")
                pagamento_premios    = st.number_input("Pagamento de Prêmios (R$)", min_value=0.0, step=0.01, format="%.2f", key="pag_premios")
                vales_despesas       = st.number_input("Vales e Despesas (R$)",      min_value=0.0, step=0.01, format="%.2f", key="vales")
            with mo2:
                retirada_cofre        = st.number_input("Retirada para Cofre (R$)",      min_value=0.0, step=0.01, format="%.2f", key="ret_cofre")
                retirada_caixa_interno= st.number_input("Retirada para Caixa Interno (R$)", min_value=0.0, step=0.01, format="%.2f", key="ret_caixa_int")
                dinheiro_gaveta       = st.number_input("Dinheiro na Gaveta (R$)",      min_value=0.0, step=0.01, format="%.2f", key="din_gaveta")

            # ======================= CÁLCULOS ========================
            total_entradas = float(total_vend_bolao + total_vend_rasp + total_vend_fed + movimentacao_cielo)
            total_saidas   = float(total_comp_bolao + total_comp_rasp + total_comp_fed +
                                   pagamento_premios + vales_despesas + retirada_cofre + retirada_caixa_interno)

            saldo_calculado = float(saldo_anterior + total_entradas - total_saidas)
            diferenca_caixa = float(dinheiro_gaveta - saldo_calculado)

            # ======================== RESUMO =========================
            st.markdown("### 📊 Resumo do Fechamento")
            r1, r2, r3 = st.columns(3)
            with r1:
                st.metric("Total Entradas", f"R$ {total_entradas:,.2f}")
                st.metric("Saldo Anterior", f"R$ {saldo_anterior:,.2f}")
            with r2:
                st.metric("Total Saídas", f"R$ {total_saidas:,.2f}")
                st.metric("Saldo Calculado", f"R$ {saldo_calculado:,.2f}")
            with r3:
                st.metric("Dinheiro na Gaveta", f"R$ {dinheiro_gaveta:,.2f}")
                if abs(diferenca_caixa) < 0.005:
                    st.success(f"✅ Caixa Fechado: R$ {diferenca_caixa:,.2f}")
                elif diferenca_caixa > 0:
                    st.warning(f"⚠️ Sobra: R$ {diferenca_caixa:,.2f}")
                else:
                    st.error(f"❌ Falta: R$ {abs(diferenca_caixa):,.2f}")

            # ================== SALVAR FECHAMENTO ====================
            if st.form_submit_button("💾 Salvar Fechamento", use_container_width=True):
                try:
                    # Prevenir duplicidade (mesmo PDV e data)
                    try:
                        exist = buscar_dados(spreadsheet, sheet_name)
                        df_exist = pd.DataFrame(exist)
                        dup = False
                        if not df_exist.empty:
                            df_exist["Data_Fechamento"] = pd.to_datetime(df_exist["Data_Fechamento"], errors="coerce").dt.date
                            cond = (df_exist["Data_Fechamento"] == data_fechamento) & (df_exist["PDV"] == pdv_selecionado)
                            dup = cond.any()
                        if dup:
                            st.error("❌ Já existe fechamento para este PDV nesta data.")
                            return
                    except Exception:
                        pass

                    ws = get_or_create_worksheet(spreadsheet, sheet_name, HEADERS_FECHAMENTO)
                    row = [
                        str(data_fechamento), pdv_selecionado, st.session_state.get("nome_usuario", "Operador"),
                        int(qtd_comp_bolao), float(custo_unit_bolao), float(total_comp_bolao),
                        int(qtd_comp_rasp),  float(custo_unit_rasp),  float(total_comp_rasp),
                        int(qtd_comp_fed),   float(custo_unit_fed),   float(total_comp_fed),
                        int(qtd_vend_bolao), float(preco_unit_bolao), float(total_vend_bolao),
                        int(qtd_vend_rasp),  float(preco_unit_rasp),  float(total_vend_rasp),
                        int(qtd_vend_fed),   float(preco_unit_fed),   float(total_vend_fed),
                        float(movimentacao_cielo), float(pagamento_premios), float(vales_despesas),
                        float(retirada_cofre), float(retirada_caixa_interno), float(dinheiro_gaveta),
                        float(saldo_anterior), float(saldo_calculado), float(diferenca_caixa)
                    ]
                    ws.append_row(row)
                    st.success(f"✅ Fechamento do {pdv_selecionado} salvo com sucesso!")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"❌ Erro ao salvar fechamento: {e}")

    except Exception as e:
        st.error(f"❌ Erro ao carregar fechamento da lotérica: {e}")
        st.info("🔄 Tente recarregar a página ou verifique a conexão com o Google Sheets.")
# ------------------------------------------------------------
# 📈 Gestão Lotérica — Estoque + Relatórios + Sincronização
# ------------------------------------------------------------
def render_gestao_loterica(spreadsheet):
    st.subheader("📈 Gestão Lotérica — Estoque & Relatórios")

    # Planilhas utilizadas
    SHEET_MOV = "Estoque_Loterica_Mov"
    FECH_PDV = {"PDV 1": "Fechamentos_PDV1", "PDV 2": "Fechamentos_PDV2"}
    PRODUTOS = ["Bolão", "Raspadinha", "Loteria Federal"]

    # Headers da planilha de movimentos de estoque
    HEADERS_MOV = [
        "Data", "Hora", "PDV", "Produto", "Tipo_Mov",  # Entrada | Venda | Ajuste+ | Ajuste-
        "Qtd", "Valor_Unit", "Valor_Total", "Obs",
        "Origem", "Chave_Sync"  # para evitar duplicidade na sincronização
    ]

    # garante existência da planilha de movimentos
    try:
        get_or_create_worksheet(spreadsheet, SHEET_MOV, HEADERS_MOV)
    except Exception as e:
        st.error(f"❌ Não foi possível garantir a planilha de movimentos: {e}")
        return

    # util: carrega movimentos como dataframe já tipado
    def _load_mov():
        dados = buscar_dados(spreadsheet, SHEET_MOV) or []
        df = pd.DataFrame(dados)
        if df.empty:
            df = pd.DataFrame(columns=HEADERS_MOV)
        # Tipagem
        for c in ["Qtd", "Valor_Unit", "Valor_Total"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
        return df

    # util: calcula saldo por PDV/Produto
    def _saldo_estoque(df_mov):
        if df_mov.empty:
            return pd.DataFrame(columns=["PDV", "Produto", "Saldo_Qtd", "Custo_Médio"])
        df = df_mov.copy()
        # fator de movimento
        df["fator"] = 0
        df.loc[df["Tipo_Mov"].isin(["Entrada", "Ajuste+"]), "fator"] = 1
        df.loc[df["Tipo_Mov"].isin(["Venda", "Ajuste-"]), "fator"] = -1
        df["Mov_Qtd"] = df["Qtd"] * df["fator"]

        # custo médio aproximado por PDV/produto (considera apenas entradas/ajuste+)
        df_ent = df[df["fator"] == 1].groupby(["PDV", "Produto"], as_index=False)[["Qtd", "Valor_Total"]].sum()
        if not df_ent.empty:
            df_ent["Custo_Médio"] = (df_ent["Valor_Total"] / df_ent["Qtd"]).replace([np.inf, -np.inf], 0).fillna(0)
        else:
            df_ent = pd.DataFrame(columns=["PDV", "Produto", "Qtd", "Valor_Total", "Custo_Médio"])

        df_saldo = df.groupby(["PDV", "Produto"], as_index=False)["Mov_Qtd"].sum().rename(columns={"Mov_Qtd": "Saldo_Qtd"})
        df_saldo = df_saldo.merge(df_ent[["PDV", "Produto", "Custo_Médio"]], on=["PDV", "Produto"], how="left").fillna({"Custo_Médio": 0})
        return df_saldo

    import numpy as np
    from datetime import timedelta

    tab1, tab2, tab3, tab4 = st.tabs(["📦 Estoque", "📊 Relatórios", "🧾 Conferência de Fechamentos", "🔄 Sincronização"])


    # ---------------------- TAB 1 — ESTOQUE ----------------------
    with tab1:
        st.markdown("#### 📦 Estoque Atual por PDV/Produto")

        df_mov = _load_mov()
        # filtros
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
            with colC:
                valor_custo = (df_saldo["Saldo_Qtd"] * df_saldo["Custo_Médio"]).sum()
                st.metric("Valor de custo estimado", f"R$ {valor_custo:,.2f}")

            st.dataframe(df_saldo.sort_values(["PDV", "Produto"]), use_container_width=True)

        st.markdown("---")
        st.markdown("#### ✍️ Ajuste Manual de Estoque")

        with st.form("form_ajuste_estoque", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                aj_pdv = st.selectbox("PDV", list(FECH_PDV.keys()), key="aj_pdv")
            with c2:
                aj_prod = st.selectbox("Produto", PRODUTOS, key="aj_prod")
            with c3:
                aj_tipo = st.selectbox("Tipo de Ajuste", ["Ajuste+", "Ajuste-"], key="aj_tipo")

            c4, c5 = st.columns(2)
            with c4:
                aj_qtd = st.number_input("Quantidade", min_value=0.0, step=1.0, format="%.0f", key="aj_qtd")
            with c5:
                aj_val = st.number_input("Valor Unitário (R$) (apenas p/ Ajuste+)", min_value=0.0, step=0.01, format="%.2f", key="aj_vu")

            aj_obs = st.text_input("Observações (opcional)", key="aj_obs")
            btn_aj = st.form_submit_button("💾 Registrar Ajuste", use_container_width=True)

            if btn_aj:
                try:
                    if aj_tipo == "Ajuste-" and aj_qtd <= 0:
                        st.error("Informe quantidade > 0.")
                    else:
                        ws = get_or_create_worksheet(spreadsheet, SHEET_MOV, HEADERS_MOV)
                        now_d = obter_data_brasilia()
                        now_h = obter_horario_brasilia()
                        valor_total = float(aj_qtd) * float(aj_val) if aj_tipo == "Ajuste+" else 0.0
                        row = [
                            now_d, now_h, aj_pdv, aj_prod, aj_tipo,
                            float(aj_qtd), float(aj_val), float(valor_total),
                            aj_obs, "AJUSTE_MANUAL", ""
                        ]
                        ws.append_row(row)
                        st.success("✅ Ajuste registrado.")
                        st.cache_data.clear()
                        st.experimental_rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao registrar ajuste: {e}")

    # -------------------- TAB 2 — RELATÓRIOS ---------------------
    with tab2:
        st.markdown("#### 📊 Relatórios de Compras, Vendas e Margem")
        # período
        c1, c2, c3 = st.columns(3)
        with c1:
            pdv_r = st.selectbox("PDV", ["Todos"] + list(FECH_PDV.keys()), key="rel_pdv")
        with c2:
            ini = st.date_input("Início", value=obter_date_brasilia() - timedelta(days=7), key="rel_ini")
        with c3:
            fim = st.date_input("Fim", value=obter_date_brasilia(), key="rel_fim")

        # buscar fechamentos dos PDVs e consolidar
        frames = []
        for pdv, sheet in FECH_PDV.items():
            try:
                dados = buscar_dados(spreadsheet, sheet) or []
                df = pd.DataFrame(dados)
                if df.empty:
                    continue
                df["Data_Fechamento"] = pd.to_datetime(df["Data_Fechamento"], errors="coerce").dt.date
                mask = (df["Data_Fechamento"] >= ini) & (df["Data_Fechamento"] <= fim)
                df = df[mask]
                df["PDV"] = pdv  # garante coluna
                frames.append(df)
            except Exception as e:
                st.warning(f"⚠️ Erro ao buscar {sheet}: {e}")

        if not frames:
            st.info("Sem dados no período selecionado.")
        else:
            df_all = pd.concat(frames, ignore_index=True)

            # Seleção por PDV
            if pdv_r != "Todos":
                df_all = df_all[df_all["PDV"] == pdv_r]

            # Tipagem
            cols_num = [
                "Qtd_Compra_Bolao","Custo_Unit_Bolao","Total_Compra_Bolao",
                "Qtd_Compra_Raspadinha","Custo_Unit_Raspadinha","Total_Compra_Raspadinha",
                "Qtd_Compra_LoteriaFederal","Custo_Unit_LoteriaFederal","Total_Compra_LoteriaFederal",
                "Qtd_Venda_Bolao","Preco_Unit_Bolao","Total_Venda_Bolao",
                "Qtd_Venda_Raspadinha","Preco_Unit_Raspadinha","Total_Venda_Raspadinha",
                "Qtd_Venda_LoteriaFederal","Preco_Unit_LoteriaFederal","Total_Venda_LoteriaFederal",
            ]
            for c in cols_num:
                if c in df_all.columns:
                    df_all[c] = pd.to_numeric(df_all[c], errors="coerce").fillna(0.0)

            # KPIs agregados
            total_compra = df_all[["Total_Compra_Bolao","Total_Compra_Raspadinha","Total_Compra_LoteriaFederal"]].sum().sum()
            total_venda  = df_all[["Total_Venda_Bolao","Total_Venda_Raspadinha","Total_Venda_LoteriaFederal"]].sum().sum()
            margem_bruta = total_venda - total_compra

            k1, k2, k3 = st.columns(3)
            with k1: st.metric("Total Compras", f"R$ {total_compra:,.2f}")
            with k2: st.metric("Total Vendas", f"R$ {total_venda:,.2f}")
            with k3:
                pct = (margem_bruta/total_venda*100) if total_venda > 0 else 0.0
                st.metric("Margem Bruta", f"R$ {margem_bruta:,.2f}", f"{pct:.1f}%")

            # Quebra por produto
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

            # gráfico simples
            try:
                import plotly.express as px
                df_melt = resumo.melt(id_vars="Produto", value_vars=["Compra_R$","Venda_R$","Margem_R$"], var_name="Tipo", value_name="Valor")
                fig = px.bar(df_melt, x="Produto", y="Valor", color="Tipo", barmode="group", text_auto=".2f",
                             title="Compras x Vendas x Margem por Produto")
                fig.update_layout(height=420, showlegend=True, font=dict(family="Inter, sans-serif"))
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass

        # ----------------- TAB 3 — CONFERÊNCIA DE FECHAMENTOS -----------------
    with tab3:
        import plotly.express as px
        from datetime import timedelta

        st.markdown("#### 🧾 Conferência de Fechamentos")

        # Filtros
        c1, c2, c3 = st.columns(3)
        with c1:
            pdv_conf = st.selectbox("PDV", ["Todos"] + list(FECH_PDV.keys()), key="conf_pdv")
        with c2:
            conf_ini = st.date_input("Início", value=obter_date_brasilia() - timedelta(days=7), key="conf_ini")
        with c3:
            conf_fim = st.date_input("Fim", value=obter_date_brasilia(), key="conf_fim")

        # Carregar dados dos PDVs conforme filtro
        frames = []
        for pdv, sheet in FECH_PDV.items():
            if pdv_conf != "Todos" and pdv != pdv_conf:
                continue
            try:
                dados = buscar_dados(spreadsheet, sheet) or []
                df = pd.DataFrame(dados)
                if df.empty:
                    continue
                df["Data_Fechamento"] = pd.to_datetime(df["Data_Fechamento"], errors="coerce").dt.date
                df = df[(df["Data_Fechamento"] >= conf_ini) & (df["Data_Fechamento"] <= conf_fim)]
                if df.empty:
                    continue
                df["PDV"] = pdv  # garante coluna PDV consistente
                frames.append(df)
            except Exception as e:
                st.warning(f"⚠️ Erro ao buscar {sheet}: {e}")

        if not frames:
            st.info("Sem fechamentos no período selecionado.")
        else:
            df_all = pd.concat(frames, ignore_index=True)

            # Tipagem de numéricos
            num_cols = [
                "Qtd_Compra_Bolao","Custo_Unit_Bolao","Total_Compra_Bolao",
                "Qtd_Compra_Raspadinha","Custo_Unit_Raspadinha","Total_Compra_Raspadinha",
                "Qtd_Compra_LoteriaFederal","Custo_Unit_LoteriaFederal","Total_Compra_LoteriaFederal",
                "Qtd_Venda_Bolao","Preco_Unit_Bolao","Total_Venda_Bolao",
                "Qtd_Venda_Raspadinha","Preco_Unit_Raspadinha","Total_Venda_Raspadinha",
                "Qtd_Venda_LoteriaFederal","Preco_Unit_LoteriaFederal","Total_Venda_LoteriaFederal",
                "Movimentacao_Cielo","Pagamento_Premios","Vales_Despesas",
                "Retirada_Cofre","Retirada_CaixaInterno","Dinheiro_Gaveta_Final",
                "Saldo_Anterior","Saldo_Final_Calculado","Diferenca_Caixa"
            ]
            for c in num_cols:
                if c in df_all.columns:
                    df_all[c] = pd.to_numeric(df_all[c], errors="coerce").fillna(0.0)

            # Cálculos agregados (período/PDV)
            total_compras = 0.0
            if {"Total_Compra_Bolao","Total_Compra_Raspadinha","Total_Compra_LoteriaFederal"}.issubset(df_all.columns):
                total_compras = df_all[["Total_Compra_Bolao","Total_Compra_Raspadinha","Total_Compra_LoteriaFederal"]].sum().sum()

            total_vendas = 0.0
            if {"Total_Venda_Bolao","Total_Venda_Raspadinha","Total_Venda_LoteriaFederal"}.issubset(df_all.columns):
                total_vendas = df_all[["Total_Venda_Bolao","Total_Venda_Raspadinha","Total_Venda_LoteriaFederal"]].sum().sum()

            total_entradas = total_vendas + float(df_all.get("Movimentacao_Cielo", pd.Series([0])).sum())
            total_saidas = total_compras + float(df_all.get("Pagamento_Premios", pd.Series([0])).sum()) \
                           + float(df_all.get("Vales_Despesas", pd.Series([0])).sum()) \
                           + float(df_all.get("Retirada_Cofre", pd.Series([0])).sum()) \
                           + float(df_all.get("Retirada_CaixaInterno", pd.Series([0])).sum())

            saldo_calc_soma = float(df_all.get("Saldo_Final_Calculado", pd.Series([0])).sum())
            din_gaveta_soma = float(df_all.get("Dinheiro_Gaveta_Final", pd.Series([0])).sum())
            diferenca_soma   = float(df_all.get("Diferenca_Caixa", pd.Series([din_gaveta_soma - saldo_calc_soma])).sum())

            # Cards
            k1, k2, k3, k4 = st.columns(4)
            with k1: st.metric("Total Entradas", f"R$ {total_entradas:,.2f}")
            with k2: st.metric("Total Saídas", f"R$ {total_saidas:,.2f}")
            with k3: st.metric("Saldo Final (soma)", f"R$ {saldo_calc_soma:,.2f}")
            with k4: st.metric("Diferença (soma)", f"R$ {diferenca_soma:,.2f}")

            # Tabela (ordenada por data desc / PDV)
            try:
                df_view = df_all.sort_values(by=["Data_Fechamento","PDV"], ascending=[False, True])
            except Exception:
                df_view = df_all
            st.dataframe(df_view, use_container_width=True)

            # Gráfico — Maiores movimentações no período (Top 10)
            cat_vals = []
            def _sum(col): 
                return float(df_all.get(col, pd.Series([0])).sum())

            cat_vals.extend([
                ("Compra Bolão",            _sum("Total_Compra_Bolao")),
                ("Compra Raspadinha",       _sum("Total_Compra_Raspadinha")),
                ("Compra Loteria Federal",  _sum("Total_Compra_LoteriaFederal")),
                ("Venda Bolão",             _sum("Total_Venda_Bolao")),
                ("Venda Raspadinha",        _sum("Total_Venda_Raspadinha")),
                ("Venda Loteria Federal",   _sum("Total_Venda_LoteriaFederal")),
                ("Movimentação Cielo",      _sum("Movimentacao_Cielo")),
                ("Pagamento de Prêmios",    _sum("Pagamento_Premios")),
                ("Vales/Despesas",          _sum("Vales_Despesas")),
                ("Retirada para Cofre",     _sum("Retirada_Cofre")),
                ("Retirada Caixa Interno",  _sum("Retirada_CaixaInterno")),
            ])
            df_cat = pd.DataFrame(cat_vals, columns=["Categoria","Valor"])
            df_cat = df_cat[df_cat["Valor"] != 0].sort_values("Valor", ascending=False)

            if df_cat.empty:
                st.info("Sem movimentações para o gráfico neste período.")
            else:
                fig = px.bar(df_cat.head(10), x="Categoria", y="Valor", text_auto=".2f",
                             title="Maiores movimentações no período (Top 10)")
                fig.update_layout(height=420, showlegend=False, font=dict(family="Inter, sans-serif"))
                st.plotly_chart(fig, use_container_width=True)


    # ------------------- TAB 3 — SINCRONIZAÇÃO -------------------
    with tab4:
        st.markdown("#### 🔄 Sincronizar Estoque a partir dos Fechamentos")
        s1, s2, s3 = st.columns(3)
        with s1:
            pdv_sinc = st.selectbox("PDV", list(FECH_PDV.keys()), key="sinc_pdv")
        with s2:
            ini_s = st.date_input("Início", value=obter_date_brasilia() - timedelta(days=7), key="sinc_ini")
        with s3:
            fim_s = st.date_input("Fim", value=obter_date_brasilia(), key="sinc_fim")

        if st.button("⚙️ Sincronizar estoque com base nos fechamentos", use_container_width=True):
            try:
                sheet = FECH_PDV[pdv_sinc]
                dados = buscar_dados(spreadsheet, sheet) or []
                df = pd.DataFrame(dados)
                if df.empty:
                    st.info("Nenhum fechamento encontrado.")
                    return

                df["Data_Fechamento"] = pd.to_datetime(df["Data_Fechamento"], errors="coerce").dt.date
                mask = (df["Data_Fechamento"] >= ini_s) & (df["Data_Fechamento"] <= fim_s)
                df = df[mask]
                if df.empty:
                    st.info("Sem fechamentos no período informado.")
                    return

                # carregar movimentos existentes p/ dedupe
                df_mov_exist = _load_mov()
                chaves_exist = set(df_mov_exist.get("Chave_Sync", []).tolist())

                ws = get_or_create_worksheet(spreadsheet, SHEET_MOV, HEADERS_MOV)
                add_count = 0

                for _, row in df.iterrows():
                    data = str(row.get("Data_Fechamento"))
                    hora = obter_horario_brasilia()
                    # Entradas = compras
                    compras = [
                        ("Bolão",           float(row.get("Qtd_Compra_Bolao", 0)),           float(row.get("Custo_Unit_Bolao", 0))),
                        ("Raspadinha",      float(row.get("Qtd_Compra_Raspadinha", 0)),     float(row.get("Custo_Unit_Raspadinha", 0))),
                        ("Loteria Federal", float(row.get("Qtd_Compra_LoteriaFederal", 0)), float(row.get("Custo_Unit_LoteriaFederal", 0))),
                    ]
                    # Saídas = vendas
                    vendas = [
                        ("Bolão",           float(row.get("Qtd_Venda_Bolao", 0)),           float(row.get("Preco_Unit_Bolao", 0))),
                        ("Raspadinha",      float(row.get("Qtd_Venda_Raspadinha", 0)),     float(row.get("Preco_Unit_Raspadinha", 0))),
                        ("Loteria Federal", float(row.get("Qtd_Venda_LoteriaFederal", 0)), float(row.get("Preco_Unit_LoteriaFederal", 0))),
                    ]

                    # compras → Entrada
                    for prod, qtd, vu in compras:
                        if qtd > 0:
                            chave = f"{data}|{pdv_sinc}|{prod}|ENT|{qtd}|{vu}"
                            if chave not in chaves_exist:
                                ws.append_row([data, hora, pdv_sinc, prod, "Entrada",
                                               float(qtd), float(vu), float(qtd*vu), "sync-fech", sheet, chave])
                                chaves_exist.add(chave)
                                add_count += 1

                    # vendas → Venda (saída)
                    for prod, qtd, vu in vendas:
                        if qtd > 0:
                            chave = f"{data}|{pdv_sinc}|{prod}|SAI|{qtd}|{vu}"
                            if chave not in chaves_exist:
                                ws.append_row([data, hora, pdv_sinc, prod, "Venda",
                                               float(qtd), float(vu), float(qtd*vu), "sync-fech", sheet, chave])
                                chaves_exist.add(chave)
                                add_count += 1

                st.success(f"✅ Sincronização concluída: {add_count} movimentos incluídos.")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"❌ Erro na sincronização: {e}")


# ------------------------------------------------------------
# Operações do Caixa Interno (rota "operacoes_caixa")
# ------------------------------------------------------------
def render_operacoes_caixa(spreadsheet):
    from decimal import Decimal
    st.subheader("💳 Operações do Caixa Interno")

    try:
        HEADERS = [
            "Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF",
            "Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro",
            "Status", "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"
        ]

        tab1, tab2, tab3, tab4 = st.tabs([
            "💳 Saque Cartão", "📄 Troca de Cheques", "🔄 Suprimento Caixa", "📊 Histórico"
        ])

        # --------------------------------------------------------
        # TAB 1 — Saque com Cartão
        # --------------------------------------------------------
        with tab1:
            st.markdown("### 💳 Saque com Cartão")

            with st.form("form_saque_cartao", clear_on_submit=False):
                operador = st.selectbox(
                    "👤 Operador Responsável",
                    ["Bruna", "Karina", "Edson", "Robson", "Adiel", "Lucas", "Ana Paula", "Fernanda"],
                    key="op_cartao"
                )

                c1, c2 = st.columns(2)
                with c1:
                    tipo_cartao = st.selectbox("Tipo de Cartão", ["Débito", "Crédito"])
                    valor = st.number_input("Valor do Saque (R$)", min_value=0.01, step=50.0, format="%.2f", key="valor_cartao")
                    nome = st.text_input("Nome do Cliente (Opcional)", key="nome_cartao")
                with c2:
                    cpf = st.text_input("CPF do Cliente (Opcional)", key="cpf_cartao")
                    observ = st.text_area("Observações", key="obs_cartao")

                col_sim, col_conf = st.columns(2)
                simular = col_sim.form_submit_button("🧮 Simular Operação", use_container_width=True)
                confirmar = col_conf.form_submit_button("💾 Confirmar e Salvar", use_container_width=True)

                if simular and valor > 0:
                    try:
                        if tipo_cartao == "Débito":
                            calc = calcular_taxa_cartao_debito(valor)
                        else:
                            calc = calcular_taxa_cartao_credito(valor)

                        st.markdown("---")
                        st.markdown(f"### ✅ Simulação — Cartão {tipo_cartao}")

                        c3, c4 = st.columns(2)
                        with c3:
                            pct = (float(calc["taxa_cliente"]) / float(valor)) * 100.0
                            st.metric("Taxa Percentual", f"{pct:.2f}%")
                            st.metric("Taxa em Valores", f"R$ {float(calc['taxa_cliente']):,.2f}")
                        with c4:
                            st.metric("💵 Valor a Entregar", f"R$ {float(calc['valor_liquido']):,.2f}")
                            if tipo_cartao == "Débito":
                                st.info("💡 Taxa ao cliente: 1% ")
                            else:
                                st.info("💡 Taxa ao cliente: 5,33%")

                        st.session_state.simulacao_cartao = {
                            "tipo": f"Saque Cartão {tipo_cartao}",
                            "dados": calc,
                            "valor_bruto": float(valor),
                            "nome": nome or "Não informado",
                            "cpf": cpf or "Não informado",
                            "observacoes": observ or "",
                            "operador": operador,
                        }
                    except Exception as e:
                        st.error(f"❌ Erro na simulação: {e}")

                if confirmar:
                    try:
                        sim = st.session_state.get("simulacao_cartao")
                        if not sim:
                            st.error("❌ Faça a simulação antes de confirmar!")
                        else:
                            ws = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", HEADERS)
                            taxa_pct_str = f"{(Decimal(str(sim['dados']['taxa_cliente'])) / Decimal(str(sim['valor_bruto'])) * Decimal('100')).quantize(Decimal('0.01'))}%"
                            row = [
                                obter_data_brasilia(),
                                obter_horario_brasilia(),
                                sim["operador"],
                                sim["tipo"],
                                sim["nome"],
                                sim["cpf"],
                                float(sim["valor_bruto"]),
                                float(sim["dados"]["taxa_cliente"]),
                                float(sim["dados"]["taxa_banco"]),
                                float(sim["dados"]["valor_liquido"]),
                                float(sim["dados"]["lucro"]),
                                "Concluído",
                                "",              # Data_Vencimento_Cheque (não se aplica)
                                taxa_pct_str,
                                sim["observacoes"],
                            ]
                            ws.append_row(row)
                            st.success(f"✅ {sim['tipo']} de R$ {sim['valor_bruto']:,.2f} registrado!")
                            del st.session_state["simulacao_cartao"]
                            st.cache_data.clear()
                    except Exception as e:
                        st.error(f"❌ Erro ao salvar operação: {e}")

        # --------------------------------------------------------
        # TAB 2 — Troca de Cheques
        # --------------------------------------------------------
        with tab2:
            st.markdown("### 📄 Troca de Cheques")

            with st.form("form_troca_cheque", clear_on_submit=False):
                operador = st.selectbox(
                    "👤 Operador Responsável",
                    ["Bruna", "Karina", "Edson", "Robson", "Adiel", "Lucas", "Ana Paula", "Fernanda"],
                    key="op_cheque"
                )

                c1, c2 = st.columns(2)
                with c1:
                    tipo_cheque = st.selectbox("Tipo de Cheque", ["Cheque à Vista", "Cheque Pré-datado", "Cheque com Taxa Manual"])
                    valor = st.number_input("Valor do Cheque (R$)", min_value=0.01, step=100.0, format="%.2f", key="valor_cheque")
                    nome = st.text_input("Nome do Cliente (Opcional)", key="nome_cheque")
                with c2:
                    cpf = st.text_input("CPF do Cliente (Opcional)", key="cpf_cheque")
                    observ = st.text_area("Observações", key="obs_cheque")

                # campos específicos
                dias = 0
                taxa_manual = 0.0
                data_venc = ""

                if tipo_cheque == "Cheque Pré-datado":
                    data_vencimento = st.date_input("Data de Vencimento", min_value=obter_date_brasilia())
                    dias = (data_vencimento - obter_date_brasilia()).days
                    st.info(f"📅 Dias até vencimento: {dias}")
                    data_venc = str(data_vencimento)
                elif tipo_cheque == "Cheque com Taxa Manual":
                    taxa_manual = st.number_input("Taxa Percentual (%)", min_value=0.1, max_value=50.0, step=0.1, key="pct_manual")

                col_sim, col_conf = st.columns(2)
                simular = col_sim.form_submit_button("🧮 Simular Operação", use_container_width=True)
                confirmar = col_conf.form_submit_button("💾 Confirmar e Salvar", use_container_width=True)

                if simular and valor > 0:
                    try:
                        if tipo_cheque == "Cheque à Vista":
                            calc = calcular_taxa_cheque_vista(valor)
                            data_venc = obter_data_brasilia()
                        elif tipo_cheque == "Cheque Pré-datado":
                            calc = calcular_taxa_cheque_pre_datado(valor, dias)
                        else:  # manual
                            calc = calcular_taxa_cheque_manual(valor, taxa_manual)
                            data_venc = obter_data_brasilia()

                        st.markdown("---")
                        st.markdown(f"### ✅ Simulação — {tipo_cheque}")

                        c3, c4 = st.columns(2)
                        with c3:
                            pct = (float(calc["taxa_cliente"]) / float(valor)) * 100.0
                            st.metric("Taxa Percentual", f"{pct:.2f}%")
                            st.metric("Taxa em Valores", f"R$ {float(calc['taxa_cliente']):,.2f}")
                        with c4:
                            st.metric("💵 Valor a Entregar", f"R$ {float(calc['valor_liquido']):,.2f}")
                            if tipo_cheque == "Cheque à Vista":
                                st.info("💡 Taxa de 2% sobre o valor do cheque.")
                            elif tipo_cheque == "Cheque Pré-datado":
                                st.info(f"💡 Taxa de 2% + 0,33% por dia ({dias} dias).")
                            else:
                                st.info(f"💡 Taxa manual definida: {taxa_manual:.2f}%.")

                        st.session_state.simulacao_cheque = {
                            "tipo": tipo_cheque,
                            "dados": calc,
                            "valor_bruto": float(valor),
                            "nome": nome or "Não informado",
                            "cpf": cpf or "Não informado",
                            "observacoes": observ or "",
                            "data_vencimento": data_venc,
                            "operador": operador,
                        }
                    except Exception as e:
                        st.error(f"❌ Erro na simulação: {e}")

                if confirmar:
                    try:
                        sim = st.session_state.get("simulacao_cheque")
                        if not sim:
                            st.error("❌ Faça a simulação antes de confirmar!")
                        else:
                            ws = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", HEADERS)
                            taxa_pct_str = f"{(Decimal(str(sim['dados']['taxa_cliente'])) / Decimal(str(sim['valor_bruto'])) * Decimal('100')).quantize(Decimal('0.01'))}%"
                            row = [
                                obter_data_brasilia(),
                                obter_horario_brasilia(),
                                sim["operador"],
                                sim["tipo"],
                                sim["nome"],
                                sim["cpf"],
                                float(sim["valor_bruto"]),
                                float(sim["dados"]["taxa_cliente"]),
                                float(sim["dados"]["taxa_banco"]),
                                float(sim["dados"]["valor_liquido"]),
                                float(sim["dados"]["lucro"]),
                                "Concluído",
                                sim["data_vencimento"],
                                taxa_pct_str,
                                sim["observacoes"],
                            ]
                            ws.append_row(row)
                            st.success(f"✅ {sim['tipo']} de R$ {sim['valor_bruto']:,.2f} registrada!")
                            del st.session_state["simulacao_cheque"]
                            st.cache_data.clear()
                    except Exception as e:
                        st.error(f"❌ Erro ao salvar operação: {e}")

        # --------------------------------------------------------
        # TAB 3 — Suprimento
        # --------------------------------------------------------
        with tab3:
            st.markdown("### 🔄 Suprimento do Caixa")

            with st.form("form_suprimento", clear_on_submit=True):
                operador = st.selectbox(
                    "👤 Operador Responsável",
                    ["Bruna", "Karina", "Edson", "Robson", "Adiel", "Lucas", "Ana Paula", "Fernanda"],
                    key="op_sup"
                )
                valor_sup = st.number_input("Valor do Suprimento (R$)", min_value=0.01, step=100.0, format="%.2f")
                origem = st.selectbox("Origem do Suprimento", ["Cofre Principal", "Banco", "Outro"])
                observ = st.text_area("Observações do Suprimento")

                if st.form_submit_button("💰 Registrar Suprimento", use_container_width=True):
                    try:
                        ws = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", HEADERS)
                        row = [
                            obter_data_brasilia(), obter_horario_brasilia(), operador,
                            "Suprimento", "Sistema", "N/A",
                            float(valor_sup), 0.0, 0.0, float(valor_sup), 0.0,
                            "Concluído", "", "0.00%", f"Origem: {origem}. {observ or ''}"
                        ]
                        ws.append_row(row)
                        st.success(f"✅ Suprimento de R$ {valor_sup:,.2f} registrado!")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"❌ Erro ao registrar suprimento: {e}")

        # --------------------------------------------------------
        # TAB 4 — Histórico
        # --------------------------------------------------------
        with tab4:
            st.markdown("### 📊 Histórico de Operações")

            try:
                op_data = buscar_dados(spreadsheet, "Operacoes_Caixa")
                if not op_data:
                    st.info("Nenhuma operação registrada ainda.")
                else:
                    df = pd.DataFrame(normalizar_dados_inteligente(op_data))

                    # filtros
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        tipo_filtro = st.selectbox(
                            "Tipo de Operação",
                            ["Todos", "Saque Cartão Débito", "Saque Cartão Crédito",
                             "Cheque à Vista", "Cheque Pré-datado", "Cheque com Taxa Manual", "Suprimento"]
                        )
                    with c2:
                        data_ini = st.date_input("Data Início", value=obter_date_brasilia() - timedelta(days=7))
                    with c3:
                        data_fim = st.date_input("Data Fim", value=obter_date_brasilia())

                    if tipo_filtro != "Todos":
                        df = df[df["Tipo_Operacao"] == tipo_filtro]

                    # datas
                    if not df.empty and "Data" in df.columns:
                        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
                        df = df[(df["Data"] >= pd.to_datetime(data_ini)) & (df["Data"] <= pd.to_datetime(data_fim))]

                    # ordenar e mostrar
                    if not df.empty:
                        if {"Data", "Hora"}.issubset(df.columns):
                            df = df.sort_values(by=["Data", "Hora"], ascending=False)
                        st.dataframe(df, use_container_width=True)

                        st.markdown("---")
                        st.markdown("### 📈 Estatísticas do Período")
                        c4, c5, c6 = st.columns(3)
                        with c4: st.metric("Total de Operações", len(df))
                        with c5:
                            if "Valor_Bruto" in df.columns:
                                st.metric("Total Movimentado", f"R$ {pd.to_numeric(df['Valor_Bruto'], errors='coerce').sum():,.2f}")
                        with c6:
                            if "Taxa_Cliente" in df.columns:
                                st.metric("Total em Taxas", f"R$ {pd.to_numeric(df['Taxa_Cliente'], errors='coerce').sum():,.2f}")
                    else:
                        st.info("Nenhuma operação encontrada com os filtros aplicados.")
            except Exception as e:
                st.error(f"❌ Erro ao carregar histórico: {e}")

    except Exception as e:
        st.error(f"❌ Erro ao carregar operações do caixa: {e}")
        st.info("🔄 Tente recarregar a página ou verifique a conexão com o Google Sheets.")


def render_dashboard_caixa(spreadsheet):
    st.subheader("💳 Dashboard Caixa Interno")

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
    # Categorias canônicas
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

# Função melhorada para gestão do cofre com interface dinâmica
def render_cofre(spreadsheet):
    st.subheader("🏦 Gestão do Cofre")
    try:
        HEADERS_COFRE = ["Data", "Hora", "Operador", "Tipo_Transacao", "Valor", "Destino_Origem", "Observacoes"]

        cofre_data = buscar_dados(spreadsheet, "Operacoes_Cofre")
        df_cofre = pd.DataFrame(cofre_data)

        saldo_cofre = Decimal("0")
        if not df_cofre.empty and "Tipo_Transacao" in df_cofre.columns and "Valor" in df_cofre.columns:
            df_cofre["Valor"] = pd.to_numeric(df_cofre["Valor"], errors="coerce").fillna(0)
            df_cofre["Tipo_Transacao"] = df_cofre["Tipo_Transacao"].astype(str)
            entradas = df_cofre[df_cofre["Tipo_Transacao"] == "Entrada no Cofre"]["Valor"].sum()
            saidas = df_cofre[df_cofre["Tipo_Transacao"] == "Saída do Cofre"]["Valor"].sum()
            saldo_cofre = Decimal(str(entradas)) - Decimal(str(saidas))

        st.markdown(f"""
        <div class="metric-card" style="background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);">
            <h3>R$ {saldo_cofre:,.2f}</h3>
            <p>🔒 Saldo Atual do Cofre</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        tab1, tab2 = st.tabs(["➕ Registrar Movimentação", "📋 Histórico do Cofre"])

        with tab1:
            st.markdown("#### Nova Movimentação no Cofre")
            tipo_mov = st.selectbox("Tipo de Movimentação", ["Entrada no Cofre", "Saída do Cofre"],
                                    key="tipo_mov_cofre_dinamico")

            with st.form("form_mov_cofre", clear_on_submit=True):
                valor = st.number_input("Valor da Movimentação (R$)", min_value=0.01, step=100.0, key="valor_cofre")
                destino_final = ""

                if tipo_mov == "Saída do Cofre":
                    tipo_saida = st.selectbox("Tipo de Saída:", ["Transferência para Caixa", "Pagamento de Despesa"],
                                              key=f"tipo_saida_cofre_{tipo_mov}")
                    if tipo_saida == "Transferência para Caixa":
                        destino_caixa = st.selectbox("Transferir para:", ["Caixa Interno", "Caixa Lotérica"],
                                                     key=f"destino_caixa_cofre_{tipo_saida}")
                        if destino_caixa == "Caixa Lotérica":
                            destino_pdv = st.selectbox("Selecione o PDV:", ["PDV 1", "PDV 2"],
                                                       key=f"destino_pdv_cofre_{destino_caixa}")
                            destino_final = f"{destino_caixa} - {destino_pdv}"
                        else:
                            destino_final = destino_caixa
                    else:
                        destino_final = st.text_input("Descrição da Despesa (Ex: Aluguel, Fornecedor X)",
                                                      key="descricao_despesa_cofre")
                else:
                    destino_final = st.text_input("Origem da Entrada (Ex: Banco, Sócio)",
                                                  key=f"origem_entrada_cofre_{tipo_mov}")

                observacoes = st.text_area("Observações Adicionais", key="obs_cofre")
                submitted = st.form_submit_button("💾 Salvar Movimentação", use_container_width=True)

                if submitted:
                    try:
                        cofre_sheet = get_or_create_worksheet(spreadsheet, "Operacoes_Cofre", HEADERS_COFRE)
                        cofre_sheet.append_row([
                            obter_data_brasilia(), obter_horario_brasilia(),
                            st.session_state.nome_usuario, tipo_mov,
                            float(valor), destino_final, observacoes
                        ])

                        if tipo_mov == "Saída do Cofre" and destino_final == "Caixa Interno":
                            HEADERS_CAIXA = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF",
                                             "Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro",
                                             "Status", "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]
                            caixa_sheet = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", HEADERS_CAIXA)
                            caixa_sheet.append_row([
                                obter_data_brasilia(), obter_horario_brasilia(), st.session_state.nome_usuario,
                                "Suprimento", "Sistema", "N/A",
                                float(valor), 0, 0, float(valor), 0,
                                "Concluído", "", "0.00%",
                                f"Transferência do Cofre para: {destino_final}"
                            ])
                            st.success(f"✅ Saída de R$ {valor:,.2f} do cofre registrada e suprimento criado no Caixa Interno!")
                        elif tipo_mov == "Saída do Cofre" and "Caixa Lotérica" in destino_final:
                            st.info(f"Saída para {destino_final} registrada. Integração futura com o caixa da lotérica.")
                            st.success(f"✅ Movimentação de R$ {valor:,.2f} no cofre registrada!")
                        else:
                            st.success(f"✅ Movimentação de R$ {valor:,.2f} no cofre registrada!")

                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"❌ Erro ao salvar movimentação: {str(e)}")

        with tab2:
            st.markdown("#### Histórico de Movimentações")
            if not df_cofre.empty:
                try:
                    if {"Data", "Hora"}.issubset(df_cofre.columns):
                        df_cofre_sorted = df_cofre.sort_values(by=["Data", "Hora"], ascending=False)
                        st.dataframe(df_cofre_sorted, use_container_width=True)
                    else:
                        st.dataframe(df_cofre, use_container_width=True)
                except Exception:
                    st.dataframe(df_cofre, use_container_width=True)
            else:
                st.info("Nenhuma movimentação registrada no cofre.")

    except Exception as e:
        st.error(f"❌ Erro ao carregar gestão do cofre: {str(e)}")
        st.info("🔄 Tente recarregar a página ou verifique a conexão com o Google Sheets.")


# (demais funções inalteradas…)
# ...
# Fechamento Diário do Caixa Interno (robusto)
def render_fechamento_diario_simplificado(spreadsheet):
    st.subheader("🗓️ Fechamento Caixa Interno")

    # --- Config (ajuste se quiser saldo inicial no 1º dia) ---
    SALDO_INICIAL_PADRAO = 2608.0  # usado só se não houver fechamento anterior
    TIPOS_SAQUE  = ["Saque Cartão Débito", "Saque Cartão Crédito"]
    TIPOS_CHEQUE = ["Cheque à Vista", "Cheque Pré-datado", "Cheque com Taxa Manual"]

    try:
        HEADERS_FECHAMENTO_CAIXA = [
            "Data_Fechamento", "Operador", "Saldo_Dia_Anterior",
            "Total_Saques_Cartao", "Total_Trocas_Cheque", "Total_Suprimentos",
            "Saldo_Calculado_Dia", "Dinheiro_Contado_Gaveta", "Diferenca_Caixa",
            "Observacoes_Fechamento"
        ]

        hoje  = obter_date_brasilia()
        ontem = hoje - timedelta(days=1)

        # ---------- 1) SALDO DO DIA ANTERIOR ----------
        saldo_dia_anterior = 0.0
        usou_saldo_inicial = False
        try:
            fechamentos_data = buscar_dados(spreadsheet, "Fechamento_Diario_Caixa_Interno") or []
            df_fech = pd.DataFrame(fechamentos_data)

            if not df_fech.empty:
                # normalização
                df_fech["Data_Fechamento"] = pd.to_datetime(df_fech["Data_Fechamento"], errors="coerce").dt.date
                df_fech["Saldo_Calculado_Dia"] = pd.to_numeric(df_fech.get("Saldo_Calculado_Dia", 0), errors="coerce").fillna(0.0)

                # último fechamento <= ontem (não apenas exatamente ontem)
                prev = df_fech[df_fech["Data_Fechamento"] <= ontem].sort_values("Data_Fechamento").tail(1)
                if not prev.empty:
                    saldo_dia_anterior = float(prev.iloc[0]["Saldo_Calculado_Dia"])
                else:
                    # 1º dia sem fechamento anterior → usa saldo inicial padrão
                    saldo_dia_anterior = float(SALDO_INICIAL_PADRAO)
                    usou_saldo_inicial = True
            else:
                # sem nenhum fechamento ainda
                saldo_dia_anterior = float(SALDO_INICIAL_PADRAO)
                usou_saldo_inicial = True
        except Exception as e:
            st.warning(f"⚠️ Erro ao buscar saldo anterior: {e}")
            saldo_dia_anterior = float(SALDO_INICIAL_PADRAO)
            usou_saldo_inicial = True

        msg_saldo_ant = f"**Saldo do Caixa (final dia anterior ≤ {ontem.strftime('%d/%m/%Y')}):** R$ {saldo_dia_anterior:,.2f}"
        if usou_saldo_inicial:
            msg_saldo_ant += "  \n_(usando saldo inicial padrão por não haver fechamento anterior)_"
        st.markdown(msg_saldo_ant)
        st.markdown("---")

        # ---------- 2) OPERAÇÕES DO DIA ----------
        operacoes_data = buscar_dados(spreadsheet, "Operacoes_Caixa") or []
        if not operacoes_data:
            st.info("📊 Nenhuma operação registrada para o dia de hoje.")
            operacoes_hoje = pd.DataFrame()
        else:
            df_op = pd.DataFrame(normalizar_dados_inteligente(operacoes_data))
            # tipagem
            for c in ["Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro"]:
                if c in df_op.columns:
                    df_op[c] = pd.to_numeric(df_op[c], errors="coerce").fillna(0.0)
            # data
            try:
                df_op["Data"] = pd.to_datetime(df_op["Data"], errors="coerce").dt.date
            except Exception:
                pass
            df_op.dropna(subset=["Data"], inplace=True)
            operacoes_hoje = df_op[df_op["Data"] == hoje]

        # somas canônicas do dia
        total_saques_cartao = operacoes_hoje[operacoes_hoje["Tipo_Operacao"].isin(TIPOS_SAQUE)]["Valor_Liquido"].sum()
        total_trocas_cheque = operacoes_hoje[operacoes_hoje["Tipo_Operacao"].isin(TIPOS_CHEQUE)]["Valor_Liquido"].sum()
        total_suprimentos   = operacoes_hoje[operacoes_hoje["Tipo_Operacao"] == "Suprimento"]["Valor_Bruto"].sum()

        # ---------- 3) SALDO CALCULADO DO DIA ----------
        saldo_calculado_dia = float(saldo_dia_anterior + total_suprimentos - (total_saques_cartao + total_trocas_cheque))

        # ---------- 4) ALERTA OPERACIONAL ----------
        try:
            tem_mov = len(operacoes_hoje) > 0
            tem_supr = len(operacoes_hoje[operacoes_hoje["Tipo_Operacao"] == "Suprimento"]) > 0
            if tem_mov and not tem_supr:
                st.markdown("""
                <div style="background:#fff3cd;color:#856404;border:1px solid #ffeeba;padding:10px;border-radius:10px;">
                    ⚠️ <b>Atenção:</b> Há movimentações hoje, mas <u>nenhum Suprimento foi registrado</u>.
                    Isso pode distorcer o saldo e os relatórios.
                </div>
                """, unsafe_allow_html=True)
        except Exception:
            pass

        # ---------- 5) RESUMO / KPIs ----------
        st.markdown("#### Resumo do Dia")
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Total Saques Cartão", f"R$ {total_saques_cartao:,.2f}")
        with c2: st.metric("Total Trocas Cheque", f"R$ {total_trocas_cheque:,.2f}")
        with c3: st.metric("Total Suprimentos", f"R$ {total_suprimentos:,.2f}")

        st.markdown(f"**Saldo Calculado para Hoje ({hoje.strftime('%d/%m/%Y')}):** R$ {saldo_calculado_dia:,.2f}")
        st.markdown("---")

        # ---------- 6) FORM DE REGISTRO ----------
        with st.form("form_fechamento_caixa_simplificado", clear_on_submit=True):
            st.markdown("#### Registrar Fechamento Diário")
            dinheiro_contado = st.number_input("Dinheiro Contado na Gaveta (R$)", min_value=0.0, step=10.0, format="%.2f")
            observacoes_fech = st.text_area("Observações do Fechamento (Opcional)")

            diferenca = float(dinheiro_contado - saldo_calculado_dia)
            st.markdown(f"**Diferença:** R$ {diferenca:,.2f}")

            btn = st.form_submit_button("💾 Salvar Fechamento", use_container_width=True)
            if btn:
                try:
                    # evita duplicidade de fechamento do mesmo dia
                    try:
                        existe_hoje = False
                        if not df_fech.empty:
                            existe_hoje = not df_fech[df_fech["Data_Fechamento"] == hoje].empty
                        if existe_hoje:
                            st.error("❌ Já existe um fechamento registrado para hoje. Edite/remova o registro anterior na planilha antes de lançar novamente.")
                            return
                    except Exception:
                        pass

                    if "nome_usuario" not in st.session_state:
                        st.session_state.nome_usuario = "OPERADOR"

                    ws = get_or_create_worksheet(spreadsheet, "Fechamento_Diario_Caixa_Interno", HEADERS_FECHAMENTO_CAIXA)
                    ws.append_row([
                        obter_data_brasilia(),                  # Data_Fechamento
                        st.session_state.nome_usuario,          # Operador
                        float(saldo_dia_anterior),              # Saldo_Dia_Anterior
                        float(total_saques_cartao),             # Total_Saques_Cartao
                        float(total_trocas_cheque),             # Total_Trocas_Cheque
                        float(total_suprimentos),               # Total_Suprimentos
                        float(saldo_calculado_dia),             # Saldo_Calculado_Dia
                        float(dinheiro_contado),                # Dinheiro_Contado_Gaveta
                        float(diferenca),                       # Diferenca_Caixa
                        observacoes_fech                        # Observacoes_Fechamento
                    ])
                    st.success("✅ Fechamento registrado com sucesso!")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"❌ Erro ao salvar fechamento: {e}")

        # ---------- 7) Expander de conferência (opcional) ----------
        with st.expander("🔍 Conferência rápida das somas do dia"):
            st.write(f"Linhas de hoje: {len(operacoes_hoje)}")
            if not operacoes_hoje.empty:
                st.dataframe(
                    operacoes_hoje.groupby("Tipo_Operacao", as_index=False)[
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
