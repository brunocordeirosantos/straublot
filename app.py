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

# Configuração da página
st.set_page_config(
    page_title="Sistema Unificado - Lotérica & Caixa Interno",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado para interface moderna (PRESERVADO)
st.markdown("""
<style>
    /* Importar fonte Inter */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Aplicar fonte globalmente */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
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
    
    /* Botões de ação rápida */
    .action-button {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 1rem;
        font-weight: 600;
        margin: 0.5rem;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(17, 153, 142, 0.3);
    }
    
    /* Cards de métricas */
    .metric-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        box-shadow: 0 8px 25px rgba(240, 147, 251, 0.3);
    }
    
    .metric-card h3 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
    }
    
    .metric-card p {
        margin: 0.5rem 0 0 0;
        font-size: 0.9rem;
        opacity: 0.9;
    }
    
    /* Inputs maiores para mobile */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select {
        height: 3rem;
        font-size: 1.1rem;
        border-radius: 10px;
        border: 2px solid #e1e5e9;
        padding: 0 1rem;
    }
    
    /* Alertas coloridos */
    .alert-success {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .alert-warning {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .alert-info {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    /* Responsividade mobile */
    @media (max-width: 768px) {
        .stButton > button {
            height: 4rem;
            font-size: 1.2rem;
        }
        
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input {
            height: 4rem;
            font-size: 1.3rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Configuração Google Sheets
# ---------------------------
@st.cache_resource
def init_google_sheets():
    """Inicializa conexão com Google Sheets. Cache para o recurso de conexão."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        try:
            creds_dict = dict(st.secrets["gcp_service_account"])
        except:
            with open("credentials.json") as f:
                creds_dict = json.load(f)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_url(
            "https://docs.google.com/spreadsheets/d/1rx9AfZQvCrwPdSxKj_-pTpm_l8I5JFZTjUt1fvSfLo8/edit"
        )
        return spreadsheet
    except Exception as e:
        st.error(f"Erro ao conectar com Google Sheets: {e}")
        return None

def get_or_create_worksheet(spreadsheet, sheet_name, headers):
    """Obtém worksheet existente ou cria novo"""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="30")
        worksheet.append_row(headers)
    return worksheet

@st.cache_data(ttl=60)
def buscar_dados(_spreadsheet, sheet_name):
    """Busca todos os registros de uma planilha e aplica cache de dados."""
    try:
        sheet = _spreadsheet.worksheet(sheet_name)
        return sheet.get_all_records()
    except gspread.WorksheetNotFound:
        return []
    except Exception as e:
        st.error(f"Erro ao buscar dados da planilha '{sheet_name}': {e}")
        return []

# ---------------------------
# Sistema de Acesso e Estado
# ---------------------------
if 'acesso_liberado' not in st.session_state:
    st.session_state.acesso_liberado = False
if 'perfil_usuario' not in st.session_state:
    st.session_state.perfil_usuario = None
if 'nome_usuario' not in st.session_state:
    st.session_state.nome_usuario = None
if 'simulacao_atual' not in st.session_state:
    st.session_state.simulacao_atual = None

USUARIOS = {
    "gerente": {"senha": "gerente123", "perfil": "gerente", "nome": "Gerente", "modulos": ["loterica", "caixa_interno", "cofre", "relatorios", "configuracoes"]},
    "loterica": {"senha": "loterica123", "perfil": "operador_loterica", "nome": "Operador Lotérica", "modulos": ["loterica", "relatorios_loterica"]},
    "caixa": {"senha": "caixa123", "perfil": "operador_caixa", "nome": "Operador Caixa", "modulos": ["caixa_interno", "relatorios_caixa"]}
}

def verificar_acesso():
    st.title("🏪 Sistema Unificado - Lotérica & Caixa Interno")
    st.markdown("### 🔐 Acesso ao Sistema")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("#### Selecione seu perfil:")
        perfil_selecionado = st.selectbox("Tipo de usuário:", ["Selecione...", "👑 Gerente", "🎰 Operador Lotérica", "💳 Operador Caixa"], key="perfil_select")
        if perfil_selecionado != "Selecione...":
            senha = st.text_input("Digite a senha:", type="password", key="senha_acesso")
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("🚀 Acessar Sistema", use_container_width=True):
                    mapa_perfil = {"👑 Gerente": "gerente", "🎰 Operador Lotérica": "loterica", "💳 Operador Caixa": "caixa"}
                    chave_usuario = mapa_perfil.get(perfil_selecionado)
                    if chave_usuario and senha == USUARIOS[chave_usuario]["senha"]:
                        st.session_state.acesso_liberado = True
                        st.session_state.perfil_usuario = USUARIOS[chave_usuario]["perfil"]
                        st.session_state.nome_usuario = USUARIOS[chave_usuario]["nome"]
                        st.session_state.modulos_permitidos = USUARIOS[chave_usuario]["modulos"]
                        st.success(f"✅ Acesso liberado! Bem-vindo, {USUARIOS[chave_usuario]['nome']}!")
                        st.rerun()
                    else:
                        st.error("❌ Senha incorreta!")
            with col_btn2:
                if st.button("ℹ️ Ajuda", use_container_width=True):
                    st.info("""💡 **Senhas de Teste:**\n- **Gerente**: gerente123\n- **Operador Lotérica**: loterica123\n- **Operador Caixa**: caixa123""")

# ---------------------------
# Funções de Cálculo (COM DECIMAL)
# ---------------------------
def calcular_taxa_cartao_debito(valor):
    valor_dec = Decimal(str(valor))
    taxa_cliente = (valor_dec * Decimal('0.01')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    taxa_banco = Decimal('1.00')
    lucro = taxa_cliente - taxa_banco
    valor_liquido = valor_dec - taxa_cliente
    return {"taxa_cliente": taxa_cliente, "taxa_banco": taxa_banco, "lucro": max(Decimal('0'), lucro), "valor_liquido": valor_liquido}

def calcular_taxa_cartao_credito(valor):
    valor_dec = Decimal(str(valor))
    taxa_cliente = (valor_dec * Decimal('0.0533')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    taxa_banco = (valor_dec * Decimal('0.0433')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    lucro = taxa_cliente - taxa_banco
    valor_liquido = valor_dec - taxa_cliente
    return {"taxa_cliente": taxa_cliente, "taxa_banco": taxa_banco, "lucro": max(Decimal('0'), lucro), "valor_liquido": valor_liquido}

def calcular_taxa_cheque_a_vista(valor):
    valor_dec = Decimal(str(valor))
    taxa_total = (valor_dec * Decimal('0.02')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    valor_liquido = valor_dec - taxa_total
    return {"taxa_total": taxa_total, "valor_liquido": valor_liquido}

def calcular_taxa_cheque_predatado(valor, data_cheque):
    valor_dec = Decimal(str(valor))
    hoje = date.today()
    dias = (data_cheque - hoje).days
    if dias < 0 or dias > 180: return None
    taxa_base = (valor_dec * Decimal('0.02')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    taxa_diaria = (valor_dec * Decimal('0.0033') * Decimal(dias)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    taxa_total = taxa_base + taxa_diaria
    valor_liquido = valor_dec - taxa_total
    return {"taxa_total": taxa_total, "valor_liquido": valor_liquido, "dias": dias}

def calcular_taxa_cheque_manual(valor, taxa_percentual):
    if taxa_percentual < 0: return None
    valor_dec = Decimal(str(valor))
    taxa_dec = Decimal(str(taxa_percentual))
    taxa_total = (valor_dec * (taxa_dec / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    valor_liquido = valor_dec - taxa_total
    return {"taxa_total": taxa_total, "valor_liquido": valor_liquido}

# ---------------------------
# Módulos de Renderização
# ---------------------------
def render_dashboard_caixa(spreadsheet):
    st.subheader("💳 Dashboard Caixa Interno")
    HEADERS = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]
    operacoes_data = buscar_dados(spreadsheet, "Operacoes_Caixa")
    if not operacoes_data:
        st.info("Nenhuma operação registrada para exibir o dashboard.")
        return
    try:
        df_operacoes = pd.DataFrame(operacoes_data)
        for col in ['Valor_Bruto', 'Valor_Liquido', 'Taxa_Cliente', 'Taxa_Banco', 'Lucro']:
            if col in df_operacoes.columns: df_operacoes[col] = pd.to_numeric(df_operacoes[col], errors='coerce').fillna(0)
        total_suprimentos = df_operacoes[df_operacoes['Tipo_Operacao'] == 'Suprimento']['Valor_Bruto'].sum()
        tipos_de_saida = ["Saque Cartão Débito", "Saque Cartão Crédito", "Troca Cheque à Vista", "Troca Cheque Pré-datado", "Troca Cheque com Taxa Manual"]
        total_saques_liquidos = df_operacoes[df_operacoes['Tipo_Operacao'].isin(tipos_de_saida)]['Valor_Liquido'].sum()
        saldo_caixa = total_suprimentos - total_saques_liquidos
        hoje_str = str(date.today())
        operacoes_de_hoje = df_operacoes[df_operacoes['Data'] == hoje_str]
        operacoes_hoje_count = len(operacoes_de_hoje)
        valor_saque_hoje = operacoes_de_hoje[operacoes_de_hoje['Tipo_Operacao'].isin(tipos_de_saida)]['Valor_Bruto'].sum()
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.markdown(f"""<div class="metric-card" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);"><h3>R$ {saldo_caixa:,.2f}</h3><p>💰 Saldo do Caixa</p></div>""", unsafe_allow_html=True)
        with col2: st.markdown(f"""<div class="metric-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);"><h3>R$ {valor_saque_hoje:,.2f}</h3><p>💳 Valor Saque Hoje</p></div>""", unsafe_allow_html=True)
        with col3: st.markdown(f"""<div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);"><h3>{operacoes_hoje_count}</h3><p>📋 Operações Hoje</p></div>""", unsafe_allow_html=True)
        with col4:
            status_cor = "#38ef7d" if saldo_caixa > 2000 else "#f5576c"
            status_texto = "Normal" if saldo_caixa > 2000 else "Baixo"
            st.markdown(f"""<div class="metric-card" style="background: linear-gradient(135deg, {status_cor} 0%, {status_cor} 100%);"><h3>{status_texto}</h3><p>🚦 Status Caixa</p></div>""", unsafe_allow_html=True)
        st.markdown("---")
        st.subheader("📊 Resumo de Operações (Últimos 7 Dias)")
        df_operacoes['Data'] = pd.to_datetime(df_operacoes['Data'], errors='coerce')
        df_operacoes.dropna(subset=['Data'], inplace=True)
        df_recente = df_operacoes[df_operacoes['Data'] >= (datetime.now() - timedelta(days=7))]
        if not df_recente.empty:
            resumo_por_tipo = df_recente.groupby('Tipo_Operacao')['Valor_Liquido'].sum().reset_index()
            fig = px.bar(resumo_por_tipo, x='Tipo_Operacao', y='Valor_Liquido', title="Valor Líquido por Tipo de Operação", labels={'Tipo_Operacao': 'Tipo de Operação', 'Valor_Liquido': 'Valor Líquido Total (R$)'}, color='Tipo_Operacao', text_auto='.2f')
            st.plotly_chart(fig, use_container_width=True)
        if saldo_caixa < 1000: st.markdown("""<div class="alert-warning">🚨 <strong>Atenção!</strong> Saldo do caixa está muito baixo. Solicite suprimento urgente.</div>""", unsafe_allow_html=True)
        elif saldo_caixa < 2000: st.markdown("""<div class="alert-info">⚠️ <strong>Aviso:</strong> Saldo do caixa está baixo. Considere solicitar suprimento.</div>""", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Erro ao carregar dashboard: {e}")
        st.exception(e)

def render_cofre(spreadsheet):
    st.subheader("🏦 Gestão do Cofre")
    HEADERS_COFRE = ["Data", "Hora", "Operador", "Tipo_Transacao", "Valor", "Destino_Origem", "Observacoes"]
    
    cofre_data = buscar_dados(spreadsheet, "Operacoes_Cofre")
    df_cofre = pd.DataFrame(cofre_data)
    saldo_cofre = Decimal('0')
    if not df_cofre.empty:
        df_cofre['Valor'] = pd.to_numeric(df_cofre['Valor'], errors='coerce').fillna(0)
        entradas = df_cofre[df_cofre['Tipo_Transacao'] == 'Entrada no Cofre']['Valor'].sum()
        saidas = df_cofre[df_cofre['Tipo_Transacao'].str.startswith("Saída", na=False)]['Valor'].sum()
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
        with st.form("form_mov_cofre", clear_on_submit=True):
            st.markdown("#### Nova Movimentação no Cofre")
            
            tipo_mov = st.selectbox("Tipo de Movimentação", ["Entrada no Cofre", "Saída do Cofre"])
            valor = st.number_input("Valor da Movimentação (R$)", min_value=0.01, step=100.0)
            
            destino_final = ""
            if tipo_mov == "Saída do Cofre":
                destino_principal = st.selectbox("Destino Principal da Saída:", ["Caixa Interno", "Caixa Lotérica", "Outro (Despesa, etc.)"])
                if destino_principal == "Caixa Lotérica":
                    destino_pdv = st.selectbox("Selecione o PDV:", ["PDV 1", "PDV 2"])
                    destino_final = f"{destino_principal} - {destino_pdv}"
                else:
                    destino_final = destino_principal
            else:
                destino_final = st.text_input("Origem da Entrada")

            observacoes = st.text_area("Observações")
            
            submitted = st.form_submit_button("💾 Salvar Movimentação", use_container_width=True)

            if submitted:
                cofre_sheet = get_or_create_worksheet(spreadsheet, "Operacoes_Cofre", HEADERS_COFRE)
                
                nova_mov_cofre = [
                    str(date.today()), datetime.now().strftime("%H:%M:%S"), st.session_state.nome_usuario,
                    tipo_mov, float(valor), destino_final, observacoes
                ]
                cofre_sheet.append_row(nova_mov_cofre)

                if tipo_mov == "Saída do Cofre" and destino_final == "Caixa Interno":
                    HEADERS_CAIXA = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]
                    caixa_sheet = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", HEADERS_CAIXA)
                    nova_operacao_caixa = [
                        str(date.today()), datetime.now().strftime("%H:%M:%S"), st.session_state.nome_usuario,
                        "Suprimento", "Sistema", "N/A", float(valor), 0, 0, float(valor), 0, "Concluído", "", "0.00%", f"Transferência do Cofre para o {destino_final}"
                    ]
                    caixa_sheet.append_row(nova_operacao_caixa)
                    st.success(f"✅ Saída de R$ {valor:,.2f} do cofre registrada e suprimento criado no Caixa Interno!")
                
                elif "Caixa Lotérica" in destino_final:
                    st.info(f"Saída para {destino_final} registrada. A integração com o caixa da lotérica será implementada futuramente.")
                    st.success(f"✅ Movimentação de R$ {valor:,.2f} no cofre registrada com sucesso!")
                
                else:
                    st.success(f"✅ Movimentação de R$ {valor:,.2f} no cofre registrada com sucesso!")
                
                st.cache_data.clear()

    with tab2:
        st.markdown("#### Histórico de Movimentações")
        if not df_cofre.empty:
            st.dataframe(df_cofre.sort_values(by=['Data', 'Hora'], ascending=False), use_container_width=True)
        else:
            st.info("Nenhuma movimentação registrada no cofre.")

def render_form_saque_cartao(spreadsheet, tipo_cartao):
    # ... (código do formulário sem alterações)...

def render_form_cheque(spreadsheet, tipo_cheque):
    # ... (código do formulário sem alterações)...

def render_operacoes_caixa(spreadsheet):
    # ... (código do módulo sem alterações)...

def render_form_suprimento(spreadsheet):
    # ... (código do formulário sem alterações)...

# ... (outras funções de render e sistema_principal sem alterações) ...
def sistema_principal():
    spreadsheet = init_google_sheets()
    if not spreadsheet:
        st.error("Falha crítica na conexão com o Google Sheets. O aplicativo não pode continuar.")
        return
    # ...

def main():
    if not st.session_state.acesso_liberado:
        verificar_acesso()
    else:
        sistema_principal()

if __name__ == "__main__":
    main()
