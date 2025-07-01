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

def buscar_dados_operacoes(_spreadsheet, sheet_name):
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
# Dashboard Caixa Interno
# ---------------------------
def render_dashboard_caixa(spreadsheet):
    st.subheader("💳 Dashboard Caixa Interno")
    HEADERS = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]
    
    operacoes_data = buscar_dados_operacoes(spreadsheet, "Operacoes_Caixa")
    
    if not operacoes_data:
        st.info("Nenhuma operação registrada para exibir o dashboard.")
        return

    try:
        df_operacoes = pd.DataFrame(operacoes_data)
        
        for col in ['Valor_Bruto', 'Valor_Liquido', 'Taxa_Cliente', 'Taxa_Banco', 'Lucro']:
            if col in df_operacoes.columns:
                df_operacoes[col] = pd.to_numeric(df_operacoes[col], errors='coerce').fillna(0)
        
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

# ---------------------------
# Formulários de Operação
# ---------------------------
def render_form_saque_cartao(spreadsheet, tipo_cartao):
    st.markdown(f"### 💳 Saque Cartão {tipo_cartao}")
    HEADERS = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]

    col1, col2 = st.columns(2)
    with col1:
        cliente = st.text_input("Nome do Cliente (opcional):", key=f"cliente_saque_{tipo_cartao}")
        cpf = st.text_input("CPF (opcional):", key=f"cpf_saque_{tipo_cartao}")
        valor = st.number_input("Valor do Saque (R$):", min_value=0.01, value=100.0, step=10.0, key=f"valor_saque_{tipo_cartao}")
    with col2:
        observacoes = st.text_area("Observações:", height=150, key=f"obs_saque_{tipo_cartao}")

    if st.button("🧮 Simular Operação", use_container_width=True, key=f"simular_saque_{tipo_cartao}"):
        if valor > 0:
            calc = calcular_taxa_cartao_debito(valor) if tipo_cartao == "Débito" else calcular_taxa_cartao_credito(valor)
            taxa_percentual_str = "1.00%" if tipo_cartao == "Débito" else "5.33%"
            
            st.session_state.simulacao_atual = {
                "tipo_operacao": f"Saque Cartão {tipo_cartao}", "valor_bruto": valor, "cliente": cliente, "cpf": cpf,
                "taxa_cliente": calc['taxa_cliente'], "taxa_banco": calc['taxa_banco'],
                "valor_liquido": calc['valor_liquido'], "lucro": calc['lucro'], "observacoes": observacoes,
                "data_vencimento": "", "taxa_percentual": taxa_percentual_str
            }
            
            st.success(f"✅ **Simulação - Cartão {tipo_cartao}**")
            st.write(f"**Taxa Cliente ({taxa_percentual_str}):** R$ {calc['taxa_cliente']:.2f}")
            st.write(f"**💵 Valor a Entregar:** R$ {calc['valor_liquido']:.2f}")
        else:
            st.warning("O valor do saque deve ser maior que zero.")

    with st.form(f"form_saque_cartao_{tipo_cartao}", clear_on_submit=True):
        st.markdown("Clique em **Confirmar** para salvar a última operação simulada.")
        if st.session_state.get('simulacao_atual'):
            sim = st.session_state.simulacao_atual
            if sim['tipo_operacao'] == f"Saque Cartão {tipo_cartao}":
                 st.info(f"Resumo: Entregar R$ {sim['valor_liquido']:.2f} para {sim['cliente'] or 'cliente'}")
        
        submitted = st.form_submit_button("💾 Confirmar e Salvar", use_container_width=True)
        if submitted:
            simulacao = st.session_state.get('simulacao_atual')
            if simulacao and simulacao['tipo_operacao'] == f"Saque Cartão {tipo_cartao}":
                caixa_sheet = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", HEADERS)
                nova_operacao = [
                    str(date.today()), datetime.now().strftime("%H:%M:%S"), st.session_state.nome_usuario,
                    simulacao['tipo_operacao'], simulacao['cliente'] or "Não informado", simulacao['cpf'] or "Não informado",
                    float(simulacao['valor_bruto']), float(simulacao['taxa_cliente']), float(simulacao['taxa_banco']),
                    float(simulacao['valor_liquido']), float(simulacao['lucro']), "Concluído", simulacao['data_vencimento'],
                    simulacao['taxa_percentual'], simulacao['observacoes']
                ]
                caixa_sheet.append_row(nova_operacao)
                st.success(f"✅ Operação registrada com sucesso!")
                st.session_state.simulacao_atual = None
            else:
                st.error("Nenhuma simulação válida encontrada. Por favor, clique em 'Simular Operação' primeiro.")

def render_form_cheque(spreadsheet, tipo_cheque):
    st.markdown(f"### 📄 {tipo_cheque}")
    HEADERS = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]

    col1, col2 = st.columns(2)
    with col1:
        cliente = st.text_input("Nome do Cliente:", key=f"cliente_ch_{tipo_cheque}")
        cpf = st.text_input("CPF do Cliente:", key=f"cpf_ch_{tipo_cheque}")
        valor = st.number_input("Valor do Cheque (R$):", min_value=0.01, value=1000.0, step=50.0, key=f"valor_ch_{tipo_cheque}")
    with col2:
        banco = st.text_input("Banco Emissor:", key=f"banco_ch_{tipo_cheque}")
        numero_cheque = st.text_input("Número do Cheque:", key=f"numero_ch_{tipo_cheque}")
        data_cheque = st.date_input("Bom para (data do cheque):", value=date.today(), key=f"data_ch_{tipo_cheque}")
    
    taxa_manual = 0.0
    if tipo_cheque == "Cheque com Taxa Manual":
        taxa_manual = st.number_input("Taxa a ser cobrada (%):", min_value=0.1, value=5.0, step=0.1, format="%.2f", key="taxa_ch_manual")
    
    observacoes = st.text_area("Observações Adicionais:", height=150, key=f"obs_ch_{tipo_cheque}")

    if st.button("🧮 Simular Operação", use_container_width=True, key=f"simular_ch_{tipo_cheque}"):
        if valor > 0:
            calc = None
            taxa_percentual_str = ""
            if tipo_cheque == "Cheque à Vista":
                calc = calcular_taxa_cheque_a_vista(valor)
                if calc: taxa_percentual_str = "2.00%"
            elif tipo_cheque == "Cheque Pré-datado":
                calc = calcular_taxa_cheque_predatado(valor, data_cheque)
                if calc:
                    taxa_efetiva = (calc['taxa_total'] / Decimal(str(valor))) * 100
                    taxa_percentual_str = f"{taxa_efetiva:.2f}%"
            elif tipo_cheque == "Cheque com Taxa Manual":
                calc = calcular_taxa_cheque_manual(valor, taxa_manual)
                if calc: taxa_percentual_str = f"{taxa_manual:.2f}%"
            
            # --- CORREÇÃO APLICADA AQUI ---
            # Só executa o bloco se o cálculo foi bem-sucedido
            if calc:
                st.session_state.simulacao_atual = {
                    "tipo_operacao": f"Troca {tipo_cheque}", "valor_bruto": valor, "cliente": cliente, "cpf": cpf,
                    "taxa_cliente": calc['taxa_total'], "taxa_banco": 0, "valor_liquido": calc['valor_liquido'],
                    "lucro": calc['taxa_total'], "observacoes": f"Banco: {banco}, Cheque: {numero_cheque}. {observacoes}",
                    "data_vencimento": str(data_cheque), "taxa_percentual": taxa_percentual_str
                }
                st.success(f"✅ **Simulação - {tipo_cheque}**")
                if "dias" in calc: st.write(f"**Prazo:** {calc['dias']} dias")
                st.write(f"**Taxa Cliente ({taxa_percentual_str}):** R$ {calc['taxa_total']:.2f}")
                st.write(f"**💵 Valor a Entregar:** R$ {calc['valor_liquido']:.2f}")
            else:
                st.error("Não foi possível gerar a simulação. Verifique os dados (ex: prazo do cheque).")
        else:
            st.warning("O valor do cheque deve ser maior que zero.")

    with st.form(f"form_cheque_{tipo_cheque}", clear_on_submit=True):
        st.markdown("Clique em **Confirmar** para salvar a última operação simulada.")
        if st.session_state.get('simulacao_atual'):
            sim = st.session_state.simulacao_atual
            if sim['tipo_operacao'] == f"Troca {tipo_cheque}":
                 st.info(f"Resumo: Entregar R$ {sim['valor_liquido']:.2f} para {sim['cliente'] or 'cliente'}")

        submitted = st.form_submit_button("💾 Confirmar Troca", use_container_width=True)
        if submitted:
            simulacao = st.session_state.get('simulacao_atual')
            if simulacao and simulacao['tipo_operacao'] == f"Troca {tipo_cheque}":
                caixa_sheet = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", HEADERS)
                nova_operacao = [
                    str(date.today()), datetime.now().strftime("%H:%M:%S"), st.session_state.nome_usuario,
                    simulacao['tipo_operacao'], simulacao['cliente'] or "Não informado", simulacao['cpf'] or "Não informado",
                    float(simulacao['valor_bruto']), float(simulacao['taxa_cliente']), float(simulacao['taxa_banco']),
                    float(simulacao['valor_liquido']), float(simulacao['lucro']), "Concluído", simulacao['data_vencimento'],
                    simulacao['taxa_percentual'], simulacao['observacoes']
                ]
                caixa_sheet.append_row(nova_operacao)
                st.success(f"✅ Operação registrada com sucesso!")
                st.session_state.simulacao_atual = None
            else:
                st.error("Nenhuma simulação válida encontrada. Por favor, clique em 'Simular Operação' primeiro.")
def render_operacoes_caixa(spreadsheet):
    if 'simulacao_atual' not in st.session_state or st.session_state.pagina_atual != 'operacoes_caixa':
        st.session_state.simulacao_atual = None
    st.subheader("💸 Operações do Caixa Interno")
    tab1, tab2 = st.tabs(["➕ Nova Operação", "📋 Histórico"])
    
    with tab1:
        tipo_operacao = st.selectbox("Selecione o Tipo de Operação:",
            ["Saque Cartão Débito", "Saque Cartão Crédito", "Cheque à Vista", "Cheque Pré-datado", "Cheque com Taxa Manual", "Suprimento Caixa"],
            on_change=lambda: st.session_state.update(simulacao_atual=None))
        
        if tipo_operacao == "Saque Cartão Débito": render_form_saque_cartao(spreadsheet, "Débito")
        elif tipo_operacao == "Saque Cartão Crédito": render_form_saque_cartao(spreadsheet, "Crédito")
        elif tipo_operacao == "Cheque à Vista": render_form_cheque(spreadsheet, "Cheque à Vista")
        elif tipo_operacao == "Cheque Pré-datado": render_form_cheque(spreadsheet, "Cheque Pré-datado")
        elif tipo_operacao == "Cheque com Taxa Manual": render_form_cheque(spreadsheet, "Cheque com Taxa Manual")
        elif tipo_operacao == "Suprimento Caixa": render_form_suprimento(spreadsheet)
    
    with tab2:
        try:
            HEADERS = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]
            data = buscar_dados_operacoes(spreadsheet, "Operacoes_Caixa")

            if data:
                df = pd.DataFrame(data)
                for col in ['Valor_Bruto', 'Taxa_Cliente', 'Taxa_Banco', 'Valor_Liquido', 'Lucro']:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                for col in HEADERS:
                    if col not in df.columns: df[col] = ''
                col1, col2, col3 = st.columns(3)
                with col1: filtro_data = st.date_input("Filtrar por data:", value=None, key="filtro_data_hist")
                with col2:
                    tipos_unicos = df['Tipo_Operacao'].unique() if 'Tipo_Operacao' in df.columns else []
                    filtro_tipo = st.selectbox("Filtrar por tipo:", ["Todos"] + list(tipos_unicos))
                with col3: filtro_operador = st.selectbox("Filtrar por operador:", ["Todos"] + list(df['Operador'].unique()) if 'Operador' in df.columns else ["Todos"])
                df_filtrado = df.copy()
                if filtro_data and 'Data' in df.columns: df_filtrado = df_filtrado[df_filtrado['Data'] == str(filtro_data)]
                if filtro_tipo != "Todos" and 'Tipo_Operacao' in df.columns: df_filtrado = df_filtrado[df_filtrado['Tipo_Operacao'] == filtro_tipo]
                if filtro_operador != "Todos" and 'Operador' in df.columns: df_filtrado = df_filtrado[df_filtrado['Operador'] == filtro_operador]
                st.dataframe(df_filtrado, use_container_width=True)
                if not df_filtrado.empty and 'Valor_Bruto' in df_filtrado.columns:
                    df_filtrado['Valor_Bruto'] = pd.to_numeric(df_filtrado['Valor_Bruto'], errors='coerce').fillna(0)
                    df_filtrado['Lucro'] = pd.to_numeric(df_filtrado['Lucro'], errors='coerce').fillna(0)
                    total_operacoes = len(df_filtrado)
                    total_valor = df_filtrado['Valor_Bruto'].sum()
                    total_lucro = df_filtrado['Lucro'].sum()
                    col1_total, col2_total, col3_total = st.columns(3)
                    with col1_total: st.metric("Total de Operações (Filtro)", total_operacoes)
                    with col2_total: st.metric("Valor Total (Filtro)", f"R$ {total_valor:,.2f}")
                    with col3_total: st.metric("Lucro Total (Filtro)", f"R$ {total_lucro:,.2f}")
            else:
                st.info("📋 Nenhuma operação registrada ainda.")
        except Exception as e:
            st.error(f"Erro ao carregar histórico: {e}")

# ---------------------------
# Outras Funções
# ---------------------------
def render_form_suprimento(spreadsheet):
    st.markdown("### 💰 Suprimento do Caixa")
    HEADERS = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]
    if st.session_state.perfil_usuario != "gerente":
        st.error("❌ Apenas o gerente pode realizar suprimentos do cofre!")
        return
    with st.form("form_suprimento", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            valor_suprimento = st.number_input("Valor do Suprimento (R$):", min_value=50.0, max_value=10000.0, value=500.0, step=50.0)
            origem = st.selectbox("Origem do Suprimento:", ["Cofre Principal", "Depósito Bancário", "Outro"])
        with col2:
            observacoes = st.text_area("Observações:", height=100, placeholder="Motivo do suprimento, autorização, etc...")
        submitted = st.form_submit_button("💾 Confirmar Suprimento", use_container_width=True)
        if submitted:
            caixa_sheet = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", HEADERS)
            nova_operacao = [
                str(date.today()), datetime.now().strftime("%H:%M:%S"), st.session_state.nome_usuario,
                "Suprimento", "Sistema", "N/A", valor_suprimento, 0, 0, valor_suprimento, 0,
                "Concluído", "", "0.00%", f"Origem: {origem}. {observacoes}"
            ]
            caixa_sheet.append_row(nova_operacao)
            st.success("✅ Suprimento registrado com sucesso!")

def render_dashboard_loterica(spreadsheet):
    st.subheader("🎰 Dashboard Lotérica")
    st.info("🚧 Em desenvolvimento.")

def render_cofre(spreadsheet):
    st.subheader("🏦 Gestão do Cofre")
    st.info("🚧 Em desenvolvimento.")
    
def render_relatorios_gerenciais(spreadsheet):
    st.subheader("📈 Relatórios Gerenciais")
    st.info("🚧 Em desenvolvimento.")
    
def render_lancamentos_loterica(spreadsheet):
    st.subheader("💰 Lançamentos Lotérica")
    st.info("🚧 Em desenvolvimento.")
    
def render_estoque(spreadsheet):
    st.subheader("📦 Gestão de Estoque")
    st.info("🚧 Em desenvolvimento.")
    
def render_relatorios_caixa(spreadsheet):
    st.subheader("📊 Relatórios do Caixa")
    st.info("🚧 Em desenvolvimento.")

# ---------------------------
# Sistema Principal
# ---------------------------
def sistema_principal():
    spreadsheet = init_google_sheets()
    if not spreadsheet:
        st.error("Falha crítica na conexão com o Google Sheets. O aplicativo não pode continuar.")
        return

    col1, col2 = st.columns([4, 1])
    with col1:
        if st.session_state.perfil_usuario == "gerente": st.title("👑 Dashboard Gerencial - Sistema Unificado")
        elif st.session_state.perfil_usuario == "operador_loterica": st.title("🎰 Sistema Lotérica")
        else: st.title("💳 Sistema Caixa Interno")
    with col2:
        st.write(f"**{st.session_state.nome_usuario}**")
        if st.button("🚪 Sair"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    st.sidebar.title("📋 Menu Principal")
    st.sidebar.success(f"✅ {st.session_state.nome_usuario}")
    st.sidebar.success("🌐 Conectado ao Google Sheets")
    st.sidebar.markdown("---")
    
    paginas = {
        "gerente": {"Dashboard Caixa": "dashboard_caixa", "Operações Caixa": "operacoes_caixa", "Gestão do Cofre": "cofre", "Dashboard Lotérica": "dashboard_loterica", "Relatórios Gerenciais": "relatorios_gerenciais"},
        "operador_loterica": {"Dashboard Lotérica": "dashboard_loterica", "Lançamentos Lotérica": "lancamentos_loterica", "Estoque Lotérica": "estoque"},
        "operador_caixa": {"Dashboard Caixa": "dashboard_caixa", "Operações Caixa": "operacoes_caixa", "Relatórios Caixa": "relatorios_caixa"}
    }
    
    if 'pagina_atual' not in st.session_state:
        st.session_state.pagina_atual = list(paginas[st.session_state.perfil_usuario].values())[0]

    for nome, chave in paginas[st.session_state.perfil_usuario].items():
        if st.sidebar.button(nome, use_container_width=True, key=f"btn_{chave}"):
            st.session_state.pagina_atual = chave
            st.rerun()

    paginas_render = {
        "dashboard_caixa": render_dashboard_caixa, "operacoes_caixa": render_operacoes_caixa,
        "cofre": render_cofre, "dashboard_loterica": render_dashboard_loterica,
        "relatorios_gerenciais": render_relatorios_gerenciais, "lancamentos_loterica": render_lancamentos_loterica,
        "estoque": render_estoque, "relatorios_caixa": render_relatorios_caixa
    }
    paginas_render[st.session_state.pagina_atual](spreadsheet)

def main():
    if not st.session_state.acesso_liberado:
        verificar_acesso()
    else:
        sistema_principal()

if __name__ == "__main__":
    main()
