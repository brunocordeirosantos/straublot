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

# CSS customizado para interface moderna
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
    """Inicializa conexão com Google Sheets"""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Carrega credenciais do secrets (para deploy) ou arquivo local (para desenvolvimento)
        try:
            # Tenta carregar do Streamlit secrets (deploy)
            creds_dict = dict(st.secrets["gcp_service_account"])
        except:
            # Fallback para arquivo local (desenvolvimento)
            with open("credentials.json") as f:
                creds_dict = json.load(f)
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Abre a planilha
        spreadsheet = client.open_by_url(
            "https://docs.google.com/spreadsheets/d/1rx9AfZQvCrwPdSxKj_-pTpm_l8I5JFZTjUt1fvSfLo8/edit"
        )
        
        return client, spreadsheet
    except Exception as e:
        st.error(f"Erro ao conectar com Google Sheets: {e}")
        return None, None

# Função para obter ou criar worksheet
def get_or_create_worksheet(spreadsheet, sheet_name, headers):
    """Obtém worksheet existente ou cria novo"""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="20")
        worksheet.append_row(headers)
    return worksheet

# ---------------------------
# Sistema de Acesso com Perfis
# ---------------------------
if 'acesso_liberado' not in st.session_state:
    st.session_state.acesso_liberado = False
if 'perfil_usuario' not in st.session_state:
    st.session_state.perfil_usuario = None
if 'nome_usuario' not in st.session_state:
    st.session_state.nome_usuario = None

# Configuração de usuários e perfis
USUARIOS = {
    "gerente": {
        "senha": "gerente123",
        "perfil": "gerente",
        "nome": "Gerente",
        "modulos": ["loterica", "caixa_interno", "cofre", "relatorios", "configuracoes"]
    },
    "loterica": {
        "senha": "loterica123", 
        "perfil": "operador_loterica",
        "nome": "Operador Lotérica",
        "modulos": ["loterica", "relatorios_loterica"]
    },
    "caixa": {
        "senha": "caixa123",
        "perfil": "operador_caixa", 
        "nome": "Operador Caixa",
        "modulos": ["caixa_interno", "relatorios_caixa"]
    }
}

def verificar_acesso():
    st.title("🏪 Sistema Unificado - Lotérica & Caixa Interno")
    st.markdown("### 🔐 Acesso ao Sistema")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("#### Selecione seu perfil:")
        
        perfil_selecionado = st.selectbox(
            "Tipo de usuário:",
            ["Selecione...", "👑 Gerente", "🎰 Operador Lotérica", "💳 Operador Caixa"],
            key="perfil_select"
        )
        
        if perfil_selecionado != "Selecione...":
            senha = st.text_input("Digite a senha:", type="password", key="senha_acesso")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("🚀 Acessar Sistema", use_container_width=True):
                    # Mapear seleção para chave do usuário
                    mapa_perfil = {
                        "👑 Gerente": "gerente",
                        "🎰 Operador Lotérica": "loterica", 
                        "💳 Operador Caixa": "caixa"
                    }
                    
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
                    st.info("""
                    💡 **Senhas de Teste:**
                    - **Gerente**: gerente123
                    - **Operador Lotérica**: loterica123  
                    - **Operador Caixa**: caixa123
                    """)

# ---------------------------
# Funções de Cálculo do Caixa Interno
# ---------------------------
def calcular_taxa_cartao_debito(valor):
    """Calcula taxa para saque de cartão débito"""
    taxa_cliente = valor * 0.01  # 1% sobre o valor
    taxa_banco = 1.00  # R$ 1,00 fixo por operação
    lucro = taxa_cliente - taxa_banco
    valor_liquido = valor - taxa_cliente
    
    return {
        "taxa_cliente": taxa_cliente,
        "taxa_banco": taxa_banco,
        "lucro": max(0, lucro),
        "valor_liquido": valor_liquido
    }

def calcular_taxa_cartao_credito(valor):
    """Calcula taxa para saque de cartão crédito"""
    taxa_cliente = valor * 0.0533  # 5,33% sobre o valor
    taxa_banco = valor * 0.0433   # 4,33% sobre o valor
    lucro = taxa_cliente - taxa_banco
    valor_liquido = valor - taxa_cliente
    
    return {
        "taxa_cliente": taxa_cliente,
        "taxa_banco": taxa_banco,
        "lucro": max(0, lucro),
        "valor_liquido": valor_liquido
    }

def calcular_taxa_cheque_a_vista(valor):
    """Calcula taxa para troca de cheque à vista (taxa fixa de 2%)"""
    taxa_total = valor * 0.02
    valor_liquido = valor - taxa_total
    return {"taxa_total": taxa_total, "valor_liquido": valor_liquido}

def calcular_taxa_cheque_predatado(valor, data_cheque):
    """Calcula taxa para troca de cheque pré-datado (2% base + 0.33% ao dia)"""
    hoje = date.today()
    data_venc = data_cheque
    
    taxa_base = valor * 0.02
    
    if data_venc > hoje:
        dias = (data_venc - hoje).days
        if dias > 180:
            return None 
        taxa_diaria = valor * 0.0033 * dias
    else:
        dias = 0
        taxa_diaria = 0

    taxa_total = taxa_base + taxa_diaria
    valor_liquido = valor - taxa_total
    
    return {
        "taxa_total": taxa_total,
        "valor_liquido": valor_liquido,
        "dias": dias
    }

def calcular_taxa_cheque_manual(valor, taxa_percentual):
    """Calcula taxa para troca de cheque com taxa manual"""
    if taxa_percentual < 0:
        return None
    
    taxa_total = valor * (taxa_percentual / 100)
    valor_liquido = valor - taxa_total
    return {"taxa_total": taxa_total, "valor_liquido": valor_liquido}

# ---------------------------
# Dashboard Caixa Interno
# ---------------------------
def render_dashboard_caixa(spreadsheet):
    st.subheader("💳 Dashboard Caixa Interno")
    
    try:
        # Carregar dados das operações do caixa
        caixa_sheet = get_or_create_worksheet(
            spreadsheet,
            "Operacoes_Caixa",
            ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", 
             "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", "Data_Vencimento_Cheque", "Observacoes"]
        )
        
        # Obter dados e converter para DataFrame
        operacoes_data = caixa_sheet.get_all_records()
        df_operacoes = pd.DataFrame(operacoes_data)

        if df_operacoes.empty:
            st.info("Nenhuma operação registrada para exibir o dashboard.")
            return

        # Garantir que colunas numéricas sejam do tipo correto para evitar erros
        for col in ['Valor_Bruto', 'Valor_Liquido', 'Taxa_Cliente', 'Taxa_Banco', 'Lucro']:
            if col in df_operacoes.columns:
                df_operacoes[col] = pd.to_numeric(df_operacoes[col], errors='coerce').fillna(0)

        # --- LÓGICA DE CÁLCULO DO SALDO CORRIGIDA ---
        total_suprimentos = df_operacoes[df_operacoes['Tipo_Operacao'] == 'Suprimento']['Valor_Bruto'].sum()
        
        # Define quais operações são consideradas saídas de dinheiro
        tipos_de_saida = ["Saque Cartão Débito", "Saque Cartão Crédito", "Troca Cheque à Vista", "Troca Cheque Pré-datado", "Troca Cheque Taxa Manual"]
        total_saques_liquidos = df_operacoes[df_operacoes['Tipo_Operacao'].isin(tipos_de_saida)]['Valor_Liquido'].sum()

        saldo_caixa = total_suprimentos - total_saques_liquidos
        
        # Métricas do dia
        hoje_str = str(date.today())
        operacoes_de_hoje = df_operacoes[df_operacoes['Data'] == hoje_str]
        
        operacoes_hoje_count = len(operacoes_de_hoje)
        valor_saque_hoje = operacoes_de_hoje[operacoes_de_hoje['Tipo_Operacao'].isin(tipos_de_saida)]['Valor_Bruto'].sum()

        # Renderizar Métricas
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
        
        # --- LÓGICA DO GRÁFICO CORRIGIDA ---
        st.subheader("📊 Resumo de Operações (Últimos 7 Dias)")
        
        df_operacoes['Data'] = pd.to_datetime(df_operacoes['Data'], errors='coerce')
        df_recente = df_operacoes[df_operacoes['Data'] >= (datetime.now() - timedelta(days=7))]
        
        if not df_recente.empty:
            # Agrupa por tipo e SOMA o Valor_Liquido
            resumo_por_tipo = df_recente.groupby('Tipo_Operacao')['Valor_Liquido'].sum().reset_index()
            
            # Altera o gráfico para barras usando o Valor_Liquido
            fig = px.bar(
                resumo_por_tipo, 
                x='Tipo_Operacao', 
                y='Valor_Liquido', 
                title="Valor Líquido por Tipo de Operação",
                labels={'Tipo_Operacao': 'Tipo de Operação', 'Valor_Liquido': 'Valor Líquido Total (R$)'},
                color='Tipo_Operacao',
                text_auto='.2f'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Alertas de Saldo
        if saldo_caixa < 1000:
            st.markdown("""
            <div class="alert-warning">
                🚨 <strong>Atenção!</strong> Saldo do caixa está muito baixo. Solicite suprimento urgente.
            </div>
            """, unsafe_allow_html=True)
        elif saldo_caixa < 2000:
            st.markdown("""
            <div class="alert-info">
                ⚠️ <strong>Aviso:</strong> Saldo do caixa está baixo. Considere solicitar suprimento.
            </div>
            """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Erro ao carregar dashboard: {e}")
        st.exception(e)

# ---------------------------
# Formulários de Operação
# ---------------------------
def render_form_saque_cartao(spreadsheet, tipo_cartao):
    st.markdown(f"### 💳 Saque Cartão {tipo_cartao}")
    NOVA_COLUNA_HEADER = "Data_Vencimento_Cheque"

    col1, col2 = st.columns(2)
    with col1:
        cliente = st.text_input("Nome do Cliente (opcional):", placeholder="Digite o nome completo", key=f"cliente_saque_{tipo_cartao}")
        cpf = st.text_input("CPF (opcional):", placeholder="000.000.000-00", key=f"cpf_saque_{tipo_cartao}")
        valor = st.number_input("Valor do Saque (R$):", min_value=10.0, max_value=5000.0, value=100.0, step=10.0, key=f"valor_saque_{tipo_cartao}")
    with col2:
        observacoes = st.text_area("Observações:", height=100, placeholder="Informações adicionais...", key=f"obs_saque_{tipo_cartao}")

    if st.button("🧮 Simular Operação", use_container_width=True, key=f"simular_saque_{tipo_cartao}"):
        if valor > 0:
            calc = calcular_taxa_cartao_debito(valor) if tipo_cartao == "Débito" else calcular_taxa_cartao_credito(valor)
            st.success(f"✅ **Simulação - Cartão {tipo_cartao}**")
            st.write(f"**Taxa Cliente:** R$ {calc['taxa_cliente']:.2f}")
            st.write(f"**Taxa Banco:** R$ {calc['taxa_banco']:.2f}")
            st.write(f"**💵 Valor a Entregar:** R$ {calc['valor_liquido']:.2f}")

    with st.form(f"form_saque_cartao_{tipo_cartao}", clear_on_submit=True):
        st.markdown("#### 💾 Confirmar e Salvar Operação")
        submitted = st.form_submit_button("💾 Confirmar e Salvar", use_container_width=True)
        if submitted:
            if valor > 0:
                calc = calcular_taxa_cartao_debito(valor) if tipo_cartao == "Débito" else calcular_taxa_cartao_credito(valor)
                caixa_sheet = get_or_create_worksheet(
                    spreadsheet, "Operacoes_Caixa",
                    ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", 
                     "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", NOVA_COLUNA_HEADER, "Observacoes"]
                )
                nova_operacao = [
                    str(date.today()), datetime.now().strftime("%H:%M:%S"), st.session_state.nome_usuario,
                    f"Saque Cartão {tipo_cartao}", cliente or "Não informado", cpf or "Não informado",
                    valor, calc['taxa_cliente'], calc['taxa_banco'], calc['valor_liquido'], calc['lucro'],
                    "Concluído", "", observacoes
                ]
                caixa_sheet.append_row(nova_operacao)
                st.success(f"✅ Operação registrada com sucesso! Valor entregue ao cliente: R$ {calc['valor_liquido']:.2f}")
                st.balloons()
            else:
                st.error("O valor da operação deve ser maior que zero.")

def render_form_cheque_a_vista(spreadsheet):
    st.markdown("### 📄 Cheque à Vista")
    NOVA_COLUNA_HEADER = "Data_Vencimento_Cheque"

    col1, col2 = st.columns(2)
    with col1:
        cliente = st.text_input("Nome do Cliente:", key="cliente_ch_vista")
        cpf = st.text_input("CPF do Cliente:", key="cpf_ch_vista")
        valor = st.number_input("Valor do Cheque (R$):", min_value=1.0, step=50.0, key="valor_ch_vista")
    with col2:
        banco = st.text_input("Banco Emissor:", key="banco_ch_vista")
        numero_cheque = st.text_input("Número do Cheque:", key="numero_ch_vista")
        data_cheque = st.date_input("Bom para (data do cheque):", value=date.today(), key="data_ch_vista")
        observacoes = st.text_area("Observações Adicionais:", key="obs_ch_vista")

    if st.button("🧮 Simular Operação", use_container_width=True, key="simular_ch_vista"):
        if valor > 0:
            calc = calcular_taxa_cheque_a_vista(valor)
            st.success("✅ **Simulação - Cheque à Vista**")
            st.write(f"**Taxa Cliente (2%):** R$ {calc['taxa_total']:.2f}")
            st.write(f"**💵 Valor a Entregar:** R$ {calc['valor_liquido']:.2f}")

    with st.form("form_cheque_a_vista", clear_on_submit=True):
        st.markdown("#### 💾 Confirmar e Salvar Troca")
        submitted = st.form_submit_button("💾 Confirmar Troca", use_container_width=True)
        if submitted:
            if valor > 0:
                calc = calcular_taxa_cheque_a_vista(valor)
                caixa_sheet = get_or_create_worksheet(
                    spreadsheet, "Operacoes_Caixa",
                    ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", 
                     "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", NOVA_COLUNA_HEADER, "Observacoes"]
                )
                obs_final = f"Banco: {banco}, Cheque: {numero_cheque}. {observacoes}"
                nova_operacao = [
                    str(date.today()), datetime.now().strftime("%H:%M:%S"), st.session_state.nome_usuario,
                    "Troca Cheque à Vista", cliente or "Não informado", cpf or "Não informado",
                    valor, calc['taxa_total'], 0, calc['valor_liquido'], calc['taxa_total'],
                    "Concluído", str(data_cheque), obs_final
                ]
                caixa_sheet.append_row(nova_operacao)
                st.success(f"✅ Troca de cheque registrada! Valor entregue ao cliente: R$ {calc['valor_liquido']:.2f}")
            else:
                st.error("O valor do cheque deve ser maior que zero.")

def render_form_cheque_predatado(spreadsheet):
    st.markdown("### 📄 Cheque Pré-datado")
    NOVA_COLUNA_HEADER = "Data_Vencimento_Cheque"

    col1, col2 = st.columns(2)
    with col1:
        cliente = st.text_input("Nome do Cliente:", key="cliente_ch_pre")
        cpf = st.text_input("CPF do Cliente:", key="cpf_ch_pre")
        valor = st.number_input("Valor do Cheque (R$):", min_value=1.0, step=50.0, key="valor_ch_pre")
    with col2:
        banco = st.text_input("Banco Emissor:", key="banco_ch_pre")
        numero_cheque = st.text_input("Número do Cheque:", key="numero_ch_pre")
        data_cheque = st.date_input("Bom para (data do cheque):", min_value=date.today(), key="data_ch_pre")
        observacoes = st.text_area("Observações Adicionais:", key="obs_ch_pre")

    if st.button("🧮 Simular Operação", use_container_width=True, key="simular_ch_pre"):
        if valor > 0:
            calc = calcular_taxa_cheque_predatado(valor, data_cheque)
            if calc:
                st.success("✅ **Simulação - Cheque Pré-datado**")
                st.write(f"**Prazo:** {calc['dias']} dias")
                st.write(f"**Taxa Total:** R$ {calc['taxa_total']:.2f}")
                st.write(f"**💵 Valor a Entregar:** R$ {calc['valor_liquido']:.2f}")
            else:
                st.error("Prazo máximo (180 dias) excedido.")
    
    with st.form("form_cheque_predatado", clear_on_submit=True):
        st.markdown("#### 💾 Confirmar e Salvar Troca")
        submitted = st.form_submit_button("💾 Confirmar Troca", use_container_width=True)
        if submitted:
            if valor > 0:
                calc = calcular_taxa_cheque_predatado(valor, data_cheque)
                if calc:
                    caixa_sheet = get_or_create_worksheet(
                        spreadsheet, "Operacoes_Caixa",
                        ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", 
                         "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", NOVA_COLUNA_HEADER, "Observacoes"]
                    )
                    obs_final = f"Banco: {banco}, Cheque: {numero_cheque}. {observacoes}"
                    nova_operacao = [
                        str(date.today()), datetime.now().strftime("%H:%M:%S"), st.session_state.nome_usuario,
                        "Troca Cheque Pré-datado", cliente or "Não informado", cpf or "Não informado",
                        valor, calc['taxa_total'], 0, calc['valor_liquido'], calc['taxa_total'],
                        "Concluído", str(data_cheque), obs_final
                    ]
                    caixa_sheet.append_row(nova_operacao)
                    st.success(f"✅ Troca de cheque pré-datado registrada! Valor entregue: R$ {calc['valor_liquido']:.2f}")
                else:
                    st.error("Não foi possível registrar: Prazo máximo (180 dias) excedido.")
            else:
                st.error("O valor do cheque deve ser maior que zero.")

def render_form_cheque_manual(spreadsheet):
    st.markdown("### 📄 Cheque com Taxa Manual")
    NOVA_COLUNA_HEADER = "Data_Vencimento_Cheque"

    col1, col2 = st.columns(2)
    with col1:
        cliente = st.text_input("Nome do Cliente:", key="cliente_ch_manual")
        cpf = st.text_input("CPF do Cliente:", key="cpf_ch_manual")
        valor = st.number_input("Valor do Cheque (R$):", min_value=1.0, step=50.0, key="valor_ch_manual")
        taxa_manual = st.number_input("Taxa a ser cobrada (%):", min_value=0.1, value=5.0, step=0.1, format="%.2f", key="taxa_ch_manual")
    with col2:
        banco = st.text_input("Banco Emissor:", key="banco_ch_manual")
        numero_cheque = st.text_input("Número do Cheque:", key="numero_ch_manual")
        data_cheque = st.date_input("Bom para (data do cheque):", key="data_ch_manual")
        observacoes = st.text_area("Observações/Motivo da taxa:", key="obs_ch_manual")

    if st.button("🧮 Simular Operação", use_container_width=True, key="simular_ch_manual"):
        if valor > 0:
            calc = calcular_taxa_cheque_manual(valor, taxa_manual)
            if calc:
                st.success("✅ **Simulação - Cheque com Taxa Manual**")
                st.write(f"**Taxa Aplicada ({taxa_manual}%):** R$ {calc['taxa_total']:.2f}")
                st.write(f"**💵 Valor a Entregar:** R$ {calc['valor_liquido']:.2f}")
    
    with st.form("form_cheque_manual", clear_on_submit=True):
        st.markdown("#### 💾 Confirmar e Salvar Troca")
        submitted = st.form_submit_button("💾 Confirmar Troca", use_container_width=True)
        if submitted:
            if valor > 0:
                calc = calcular_taxa_cheque_manual(valor, taxa_manual)
                if calc:
                    caixa_sheet = get_or_create_worksheet(
                        spreadsheet, "Operacoes_Caixa",
                        ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", 
                         "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", NOVA_COLUNA_HEADER, "Observacoes"]
                    )
                    obs_final = f"Taxa manual de {taxa_manual}%. Banco: {banco}, Cheque: {numero_cheque}. {observacoes}"
                    nova_operacao = [
                        str(date.today()), datetime.now().strftime("%H:%M:%S"), st.session_state.nome_usuario,
                        "Troca Cheque Taxa Manual", cliente or "Não informado", cpf or "Não informado",
                        valor, calc['taxa_total'], 0, calc['valor_liquido'], calc['taxa_total'],
                        "Concluído", str(data_cheque), obs_final
                    ]
                    caixa_sheet.append_row(nova_operacao)
                    st.success(f"✅ Troca de cheque registrada! Valor entregue: R$ {calc['valor_liquido']:.2f}")
                else:
                    st.error("Não foi possível calcular a taxa.")
            else:
                st.error("O valor do cheque deve ser maior que zero.")

# ---------------------------
# Operações do Caixa Interno
# ---------------------------
def render_operacoes_caixa(spreadsheet):
    st.subheader("💸 Operações do Caixa Interno")
    
    tab1, tab2 = st.tabs(["➕ Nova Operação", "📋 Histórico"])
    
    with tab1:
        tipo_operacao = st.selectbox(
            "Selecione o Tipo de Operação:",
            [
                "Saque Cartão Débito", 
                "Saque Cartão Crédito", 
                "Cheque à Vista",
                "Cheque Pré-datado",
                "Cheque com Taxa Manual",
                "Suprimento Caixa"
            ]
        )
        
        if tipo_operacao == "Saque Cartão Débito":
            render_form_saque_cartao(spreadsheet, "Débito")
        elif tipo_operacao == "Saque Cartão Crédito":
            render_form_saque_cartao(spreadsheet, "Crédito")
        elif tipo_operacao == "Cheque à Vista":
            render_form_cheque_a_vista(spreadsheet)
        elif tipo_operacao == "Cheque Pré-datado":
            render_form_cheque_predatado(spreadsheet)
        elif tipo_operacao == "Cheque com Taxa Manual":
            render_form_cheque_manual(spreadsheet)
        elif tipo_operacao == "Suprimento Caixa":
            render_form_suprimento(spreadsheet)
    
    with tab2:
        try:
            NOVA_COLUNA_HEADER = "Data_Vencimento_Cheque"
            headers = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", 
                       "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", NOVA_COLUNA_HEADER, "Observacoes"]
            
            caixa_sheet = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", headers)
            data = caixa_sheet.get_all_records()
            
            if data:
                df = pd.DataFrame(data)
                
                for col in headers:
                    if col not in df.columns:
                        df[col] = ''
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    filtro_data = st.date_input("Filtrar por data:", value=None, key="filtro_data_hist")
                with col2:
                    tipos_unicos = df['Tipo_Operacao'].unique() if 'Tipo_Operacao' in df.columns else []
                    filtro_tipo = st.selectbox("Filtrar por tipo:", ["Todos"] + list(tipos_unicos))
                with col3:
                    filtro_operador = st.selectbox("Filtrar por operador:", 
                                                 ["Todos"] + list(df['Operador'].unique()) if 'Operador' in df.columns else ["Todos"])
                
                df_filtrado = df.copy()
                if filtro_data and 'Data' in df.columns:
                    df_filtrado = df_filtrado[df_filtrado['Data'] == str(filtro_data)]
                if filtro_tipo != "Todos" and 'Tipo_Operacao' in df.columns:
                    df_filtrado = df_filtrado[df_filtrado['Tipo_Operacao'] == filtro_tipo]
                if filtro_operador != "Todos" and 'Operador' in df.columns:
                    df_filtrado = df_filtrado[df_filtrado['Operador'] == filtro_operador]
                
                st.dataframe(df_filtrado, use_container_width=True)
                
                if not df_filtrado.empty and 'Valor_Bruto' in df_filtrado.columns:
                    df_filtrado['Valor_Bruto'] = pd.to_numeric(df_filtrado['Valor_Bruto'], errors='coerce').fillna(0)
                    df_filtrado['Lucro'] = pd.to_numeric(df_filtrado['Lucro'], errors='coerce').fillna(0)

                    total_operacoes = len(df_filtrado)
                    total_valor = df_filtrado['Valor_Bruto'].sum()
                    total_lucro = df_filtrado['Lucro'].sum()
                    
                    col1_total, col2_total, col3_total = st.columns(3)
                    with col1_total:
                        st.metric("Total de Operações (Filtro)", total_operacoes)
                    with col2_total:
                        st.metric("Valor Total (Filtro)", f"R$ {total_valor:,.2f}")
                    with col3_total:
                        st.metric("Lucro Total (Filtro)", f"R$ {total_lucro:,.2f}")
            else:
                st.info("📋 Nenhuma operação registrada ainda.")
                
        except Exception as e:
            st.error(f"Erro ao carregar histórico: {e}")

# ---------------------------
# Outras funções (simplificadas para o exemplo)
# ---------------------------
def render_dashboard_loterica(spreadsheet):
    st.subheader("🎰 Dashboard Lotérica")
    st.info("🚧 Dashboard da lotérica será implementado na próxima versão.")

def render_lancamentos_loterica(spreadsheet):
    st.subheader("💰 Lançamentos Lotérica")
    st.info("🚧 Lançamentos da lotérica serão implementados na próxima versão.")

def render_cofre(spreadsheet):
    st.subheader("🏦 Gestão do Cofre")
    st.info("🚧 Gestão do cofre será implementada na próxima versão.")

def render_estoque(spreadsheet):
    st.subheader("📦 Gestão de Estoque")
    st.info("🚧 Gestão de estoque será implementada na próxima versão.")

def render_relatorios_caixa(spreadsheet):
    st.subheader("📊 Relatórios do Caixa")
    st.info("🚧 Relatórios detalhados serão implementados na próxima versão.")

def render_relatorios_gerenciais(spreadsheet):
    st.subheader("📈 Relatórios Gerenciais")
    st.info("🚧 Relatórios gerenciais serão implementados na próxima versão.")

def render_configuracoes():
    st.subheader("⚙️ Configurações")
    st.info("🚧 Configurações serão implementadas na próxima versão.")

def render_form_suprimento(spreadsheet):
    st.markdown("### 💰 Suprimento do Caixa")
    NOVA_COLUNA_HEADER = "Data_Vencimento_Cheque"
    
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
            caixa_sheet = get_or_create_worksheet(
                spreadsheet,
                "Operacoes_Caixa",
                ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", 
                 "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", NOVA_COLUNA_HEADER, "Observacoes"]
            )
            nova_operacao = [
                str(date.today()), datetime.now().strftime("%H:%M:%S"), st.session_state.nome_usuario,
                "Suprimento", "Sistema", "N/A", valor_suprimento, 0, 0, valor_suprimento, 0,
                "Concluído", "", f"Origem: {origem}. {observacoes}"
            ]
            caixa_sheet.append_row(nova_operacao)
            st.success("✅ Suprimento registrado com sucesso!")
            st.balloons()

def render_relatorio_rapido(operacoes_data):
    st.markdown("### 📊 Relatório Rápido - Hoje")
    
    hoje_str = str(date.today())
    ops_hoje = [op for op in operacoes_data if op.get("Data") == hoje_str]
    
    if ops_hoje:
        df = pd.DataFrame(ops_hoje)
        st.dataframe(df, use_container_width=True)
        
        total_ops = len(ops_hoje)
        total_lucro = sum([float(op.get("Lucro", 0)) for op in ops_hoje])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Operações Hoje", total_ops)
        with col2:
            st.metric("Lucro Hoje", f"R$ {total_lucro:.2f}")
    else:
        st.info("📋 Nenhuma operação registrada hoje.")

# ---------------------------
# Sistema Principal
# ---------------------------
def sistema_principal():
    client, spreadsheet = init_google_sheets()
    if not client or not spreadsheet:
        st.error("❌ Não foi possível conectar ao Google Sheets. Verifique as credenciais.")
        return
    
    col1, col2 = st.columns([4, 1])
    with col1:
        if st.session_state.perfil_usuario == "gerente":
            st.title("👑 Dashboard Gerencial - Sistema Unificado")
        elif st.session_state.perfil_usuario == "operador_loterica":
            st.title("🎰 Sistema Lotérica")
        else:
            st.title("💳 Sistema Caixa Interno")
    
    with col2:
        st.write(f"**{st.session_state.nome_usuario}**")
        if st.button("🚪 Sair"):
            st.session_state.acesso_liberado = False
            st.session_state.perfil_usuario = None
            st.session_state.nome_usuario = None
            st.rerun()
    
    st.sidebar.title("📋 Menu Principal")
    st.sidebar.success(f"✅ {st.session_state.nome_usuario}")
    st.sidebar.success("🌐 Conectado ao Google Sheets")
    st.sidebar.markdown("---")
    
    if st.session_state.perfil_usuario == "gerente":
        st.sidebar.subheader("🏠 Dashboards")
        if st.sidebar.button("🎰 Dashboard Lotérica", use_container_width=True):
            st.session_state.pagina_atual = "dashboard_loterica"
            st.rerun()
        if st.sidebar.button("💳 Dashboard Caixa", use_container_width=True):
            st.session_state.pagina_atual = "dashboard_caixa"
            st.rerun()
        st.sidebar.subheader("💰 Operações")
        if st.sidebar.button("💸 Operações Caixa", use_container_width=True):
            st.session_state.pagina_atual = "operacoes_caixa"
            st.rerun()
        if st.sidebar.button("🏦 Gestão do Cofre", use_container_width=True):
            st.session_state.pagina_atual = "cofre"
            st.rerun()
        st.sidebar.subheader("📊 Relatórios")
        if st.sidebar.button("📈 Relatórios Gerenciais", use_container_width=True):
            st.session_state.pagina_atual = "relatorios_gerenciais"
            st.rerun()
    elif st.session_state.perfil_usuario == "operador_loterica":
        if st.sidebar.button("🎰 Dashboard Lotérica", use_container_width=True):
            st.session_state.pagina_atual = "dashboard_loterica"
            st.rerun()
        if st.sidebar.button("💰 Lançamentos Lotérica", use_container_width=True):
            st.session_state.pagina_atual = "lancamentos_loterica"
            st.rerun()
        if st.sidebar.button("📦 Estoque Lotérica", use_container_width=True):
            st.session_state.pagina_atual = "estoque"
            st.rerun()
    elif st.session_state.perfil_usuario == "operador_caixa":
        if st.sidebar.button("💳 Dashboard Caixa", use_container_width=True):
            st.session_state.pagina_atual = "dashboard_caixa"
            st.rerun()
        if st.sidebar.button("💸 Operações Caixa", use_container_width=True):
            st.session_state.pagina_atual = "operacoes_caixa"
            st.rerun()
        if st.sidebar.button("📊 Relatórios Caixa", use_container_width=True):
            st.session_state.pagina_atual = "relatorios_caixa"
            st.rerun()
    
    if 'pagina_atual' not in st.session_state:
        if st.session_state.perfil_usuario == "operador_caixa":
            st.session_state.pagina_atual = "dashboard_caixa"
        elif st.session_state.perfil_usuario == "operador_loterica":
            st.session_state.pagina_atual = "dashboard_loterica"
        else:
            st.session_state.pagina_atual = "dashboard_caixa"
    
    if st.session_state.pagina_atual == "dashboard_loterica":
        render_dashboard_loterica(spreadsheet)
    elif st.session_state.pagina_atual == "dashboard_caixa":
        render_dashboard_caixa(spreadsheet)
    elif st.session_state.pagina_atual == "lancamentos_loterica":
        render_lancamentos_loterica(spreadsheet)
    elif st.session_state.pagina_atual == "operacoes_caixa":
        render_operacoes_caixa(spreadsheet)
    elif st.session_state.pagina_atual == "cofre":
        render_cofre(spreadsheet)
    elif st.session_state.pagina_atual == "estoque":
        render_estoque(spreadsheet)
    elif st.session_state.pagina_atual == "relatorios_caixa":
        render_relatorios_caixa(spreadsheet)
    elif st.session_state.pagina_atual == "relatorios_gerenciais":
        render_relatorios_gerenciais(spreadsheet)
    elif st.session_state.pagina_atual == "configuracoes":
        render_configuracoes()

# ---------------------------
# Função Principal
# ---------------------------
def main():
    if not st.session_state.acesso_liberado:
        verificar_acesso()
    else:
        sistema_principal()

if __name__ == "__main__":
    main()
