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
    .alert-warning {
        background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        color: #721c24;
        border-left: 4px solid #dc3545;
    }
    
    .alert-info {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        color: #0c5460;
        border-left: 4px solid #17a2b8;
    }
    
    /* Sidebar personalizada */
    .css-1d391kg {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Esconder elementos desnecessários */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Configurações e Autenticação
# ---------------------------

# Configuração de usuários
USUARIOS = {
    "gerente": {"senha": "gerente123", "perfil": "gerente", "nome": "Gerente", "modulos": ["dashboard_loterica", "dashboard_caixa", "operacoes_caixa", "cofre", "fechamento_loterica", "relatorios"]},
    "loterica": {"senha": "loterica123", "perfil": "operador_loterica", "nome": "Operador Lotérica", "modulos": ["dashboard_loterica", "fechamento_loterica"]},
    "caixa": {"senha": "caixa123", "perfil": "operador_caixa", "nome": "Operador Caixa", "modulos": ["dashboard_caixa", "operacoes_caixa"]}
}

# Inicializar session state
if 'acesso_liberado' not in st.session_state:
    st.session_state.acesso_liberado = False
if 'simulacao_atual' not in st.session_state:
    st.session_state.simulacao_atual = None

# ---------------------------
# Conexão com Google Sheets
# ---------------------------
@st.cache_resource
def init_google_sheets():
    """Inicializa conexão com Google Sheets. Cache para o recurso de conexão."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Lógica para funcionar tanto online (deploy) quanto no seu computador (local)
        try:
            # Tenta carregar do Streamlit secrets (deploy)
            creds_dict = dict(st.secrets["gcp_service_account"])
        except:
            # Se falhar, tenta abrir o arquivo local (desenvolvimento)
            with open("credentials.json") as f:
                creds_dict = json.load(f)
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Abre a planilha
        spreadsheet = client.open_by_url(
            "https://docs.google.com/spreadsheets/d/1rx9AfZQvCrwPdSxKj_-pTpm_l8I5JFZTjUt1fvSfLo8/edit"
        )
        
        return spreadsheet
    except Exception as e:
        st.error(f"Erro ao conectar com Google Sheets: {e}")
        return None

def get_or_create_worksheet(spreadsheet, sheet_name, headers):
    try:
        return spreadsheet.worksheet(sheet_name)
    except:
        sheet = spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="20")
        sheet.append_row(headers)
        return sheet

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
# Funções de Cálculo (COM DECIMAL) - CORRIGIDAS
# ---------------------------
def calcular_taxa_cartao_debito(valor):
    """Calcula taxa para cartão débito: 1% cliente + R$ 1,00 banco"""
    valor_dec = Decimal(str(valor))
    taxa_cliente = (valor_dec * Decimal('0.01')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    taxa_banco = Decimal('1.00')
    lucro = taxa_cliente - taxa_banco
    valor_liquido = valor_dec - taxa_cliente
    
    return {
        "taxa_cliente": float(taxa_cliente), 
        "taxa_banco": float(taxa_banco), 
        "lucro": float(max(Decimal('0'), lucro)), 
        "valor_liquido": float(valor_liquido)
    }

def calcular_taxa_cartao_credito(valor):
    """Calcula taxa para cartão crédito: 5,33% cliente + 4,33% banco"""
    valor_dec = Decimal(str(valor))
    taxa_cliente = (valor_dec * Decimal('0.0533')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    taxa_banco = (valor_dec * Decimal('0.0433')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    lucro = taxa_cliente - taxa_banco
    valor_liquido = valor_dec - taxa_cliente
    
    return {
        "taxa_cliente": float(taxa_cliente), 
        "taxa_banco": float(taxa_banco), 
        "lucro": float(max(Decimal('0'), lucro)), 
        "valor_liquido": float(valor_liquido)
    }

def calcular_taxa_cheque_a_vista(valor):
    """Calcula taxa para cheque à vista: 2%"""
    valor_dec = Decimal(str(valor))
    taxa_total = (valor_dec * Decimal('0.02')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    valor_liquido = valor_dec - taxa_total
    
    return {
        "taxa_total": float(taxa_total), 
        "valor_liquido": float(valor_liquido)
    }

def calcular_taxa_cheque_predatado(valor, data_cheque):
    """Calcula taxa para cheque pré-datado: 2% + 0,33% por dia"""
    valor_dec = Decimal(str(valor))
    hoje = date.today()
    
    if isinstance(data_cheque, str):
        data_cheque = datetime.strptime(data_cheque, '%Y-%m-%d').date()
    
    dias = (data_cheque - hoje).days
    
    if dias < 0 or dias > 180:
        return None
    
    taxa_base = (valor_dec * Decimal('0.02')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    taxa_diaria = (valor_dec * Decimal('0.0033') * Decimal(dias)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    taxa_total = taxa_base + taxa_diaria
    valor_liquido = valor_dec - taxa_total
    
    return {
        "taxa_total": float(taxa_total), 
        "valor_liquido": float(valor_liquido), 
        "dias": dias
    }

def calcular_taxa_cheque_manual(valor, taxa_percentual):
    """Calcula taxa manual para cheque"""
    if taxa_percentual < 0:
        return None
    
    valor_dec = Decimal(str(valor))
    taxa_dec = Decimal(str(taxa_percentual))
    taxa_total = (valor_dec * (taxa_dec / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    valor_liquido = valor_dec - taxa_total
    
    return {
        "taxa_total": float(taxa_total), 
        "valor_liquido": float(valor_liquido)
    }

# ---------------------------
# Módulos de Renderização - CORRIGIDOS
# ---------------------------
def render_dashboard_caixa(spreadsheet):
    st.subheader("💳 Dashboard Caixa Interno")
    
    HEADERS = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", 
               "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", 
               "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]
    
    operacoes_data = buscar_dados(spreadsheet, "Operacoes_Caixa")
    
    if not operacoes_data:
        st.info("Nenhuma operação registrada para exibir o dashboard.")
        return
    
    try:
        df_operacoes = pd.DataFrame(operacoes_data)
        
        # Converter colunas numéricas
        for col in ['Valor_Bruto', 'Valor_Liquido', 'Taxa_Cliente', 'Taxa_Banco', 'Lucro']:
            if col in df_operacoes.columns:
                df_operacoes[col] = pd.to_numeric(df_operacoes[col], errors='coerce').fillna(0)
        
        # Calcular saldo do caixa
        saldo_inicial = 5000.0  # Valor inicial do caixa
        total_suprimentos = df_operacoes[df_operacoes['Tipo_Operacao'] == 'Suprimento']['Valor_Bruto'].sum()
        
        tipos_de_saida = ["Saque Cartão Débito", "Saque Cartão Crédito", "Troca Cheque à Vista", 
                         "Troca Cheque Pré-datado", "Troca Cheque com Taxa Manual"]
        total_saques_liquidos = df_operacoes[df_operacoes['Tipo_Operacao'].isin(tipos_de_saida)]['Valor_Liquido'].sum()
        
        saldo_caixa = saldo_inicial + total_suprimentos - total_saques_liquidos
        
        # Métricas do dia
        hoje_str = str(date.today())
        operacoes_de_hoje = df_operacoes[df_operacoes['Data'] == hoje_str]
        operacoes_hoje_count = len(operacoes_de_hoje)
        valor_saque_hoje = operacoes_de_hoje[operacoes_de_hoje['Tipo_Operacao'].isin(tipos_de_saida)]['Valor_Bruto'].sum()
        
        # Exibir métricas
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
        
        # Gráfico de operações
        st.subheader("📊 Resumo de Operações (Últimos 7 Dias)")
        
        df_operacoes['Data'] = pd.to_datetime(df_operacoes['Data'], errors='coerce')
        df_operacoes.dropna(subset=['Data'], inplace=True)
        df_recente = df_operacoes[df_operacoes['Data'] >= (datetime.now() - timedelta(days=7))]
        
        if not df_recente.empty:
            resumo_por_tipo = df_recente.groupby('Tipo_Operacao')['Valor_Liquido'].sum().reset_index()
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
        
        # Alertas de saldo
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

def render_form_saque_cartao(spreadsheet, tipo_cartao):
    st.markdown(f"### 💳 Saque Cartão {tipo_cartao}")
    
    HEADERS = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", 
               "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", 
               "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]
    
    # Campos do formulário
    col1, col2 = st.columns(2)
    
    with col1:
        cliente = st.text_input("Nome do Cliente (opcional):", key=f"cliente_saque_{tipo_cartao}")
        cpf = st.text_input("CPF (opcional):", key=f"cpf_saque_{tipo_cartao}")
        valor = st.number_input("Valor do Saque (R$):", min_value=0.01, value=100.0, step=10.0, key=f"valor_saque_{tipo_cartao}")
    
    with col2:
        observacoes = st.text_area("Observações:", height=150, key=f"obs_saque_{tipo_cartao}")
    
    # Botão de simulação
    if st.button("🧮 Simular Operação", use_container_width=True, key=f"simular_saque_{tipo_cartao}"):
        if valor > 0:
            # CORREÇÃO: Usar as funções corretas e armazenar no session_state
            if tipo_cartao == "Débito":
                calc = calcular_taxa_cartao_debito(valor)
                taxa_percentual_str = "1.00%"
            else:
                calc = calcular_taxa_cartao_credito(valor)
                taxa_percentual_str = "5.33%"
            
            # Armazenar simulação no session_state
            st.session_state.simulacao_atual = {
                "tipo_operacao": f"Saque Cartão {tipo_cartao}",
                "valor_bruto": valor,
                "cliente": cliente,
                "cpf": cpf,
                "taxa_cliente": calc['taxa_cliente'],
                "taxa_banco": calc['taxa_banco'],
                "valor_liquido": calc['valor_liquido'],
                "lucro": calc['lucro'],
                "observacoes": observacoes,
                "data_vencimento": "",
                "taxa_percentual": taxa_percentual_str
            }
            
            # Exibir simulação
            st.success(f"✅ **Simulação - Cartão {tipo_cartao}**")
            st.write(f"**Taxa Cliente ({taxa_percentual_str}):** R$ {calc['taxa_cliente']:.2f}")
            st.write(f"**💵 Valor a Entregar:** R$ {calc['valor_liquido']:.2f}")
            
        else:
            st.warning("O valor do saque deve ser maior que zero.")
    
    # Formulário de confirmação
    with st.form(f"form_saque_cartao_{tipo_cartao}", clear_on_submit=True):
        st.markdown("Clique em **Confirmar** para salvar a última operação simulada.")
        
        # Mostrar resumo da simulação atual
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
                    str(date.today()),
                    datetime.now().strftime("%H:%M:%S"),
                    st.session_state.nome_usuario,
                    simulacao['tipo_operacao'],
                    simulacao['cliente'] or "Não informado",
                    simulacao['cpf'] or "Não informado",
                    float(simulacao['valor_bruto']),
                    float(simulacao['taxa_cliente']),
                    float(simulacao['taxa_banco']),
                    float(simulacao['valor_liquido']),
                    float(simulacao['lucro']),
                    "Concluído",
                    simulacao['data_vencimento'],
                    simulacao['taxa_percentual'],
                    simulacao['observacoes']
                ]
                
                caixa_sheet.append_row(nova_operacao)
                st.success(f"✅ Operação registrada com sucesso!")
                st.session_state.simulacao_atual = None
                st.cache_data.clear()
            else:
                st.error("Nenhuma simulação válida encontrada. Por favor, clique em 'Simular Operação' primeiro.")

def render_form_cheque(spreadsheet, tipo_cheque):
    st.markdown(f"### 📄 {tipo_cheque}")
    
    HEADERS = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", 
               "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", 
               "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]
    
    # Campos do formulário
    col1, col2 = st.columns(2)
    
    with col1:
        cliente = st.text_input("Nome do Cliente:", key=f"cliente_ch_{tipo_cheque}")
        cpf = st.text_input("CPF do Cliente:", key=f"cpf_ch_{tipo_cheque}")
        valor = st.number_input("Valor do Cheque (R$):", min_value=0.01, value=1000.0, step=50.0, key=f"valor_ch_{tipo_cheque}")
    
    with col2:
        banco = st.text_input("Banco Emissor:", key=f"banco_ch_{tipo_cheque}")
        numero_cheque = st.text_input("Número do Cheque:", key=f"numero_ch_{tipo_cheque}")
        data_cheque = st.date_input("Bom para (data do cheque):", value=date.today(), key=f"data_ch_{tipo_cheque}")
    
    # Taxa manual para cheque com taxa manual
    taxa_manual = 0.0
    if tipo_cheque == "Cheque com Taxa Manual":
        taxa_manual = st.number_input("Taxa a ser cobrada (%):", min_value=0.1, value=5.0, step=0.1, format="%.2f", key="taxa_ch_manual")
    
    observacoes = st.text_area("Observações Adicionais:", height=150, key=f"obs_ch_{tipo_cheque}")
    
    # Botão de simulação
    if st.button("🧮 Simular Operação", use_container_width=True, key=f"simular_ch_{tipo_cheque}"):
        if valor > 0:
            calc = None
            taxa_percentual_str = ""
            
            # CORREÇÃO: Usar as funções corretas
            if tipo_cheque == "Cheque à Vista":
                calc = calcular_taxa_cheque_a_vista(valor)
                if calc:
                    taxa_percentual_str = "2.00%"
            elif tipo_cheque == "Cheque Pré-datado":
                calc = calcular_taxa_cheque_predatado(valor, data_cheque)
                if calc:
                    taxa_percentual_str = f"{(calc['taxa_total'] / valor) * 100:.2f}%"
            elif tipo_cheque == "Cheque com Taxa Manual":
                calc = calcular_taxa_cheque_manual(valor, taxa_manual)
                if calc:
                    taxa_percentual_str = f"{taxa_manual:.2f}%"
            
            if calc:
                # Armazenar simulação no session_state
                st.session_state.simulacao_atual = {
                    "tipo_operacao": f"Troca {tipo_cheque}",
                    "valor_bruto": valor,
                    "cliente": cliente,
                    "cpf": cpf,
                    "taxa_cliente": calc['taxa_total'],
                    "taxa_banco": 0,
                    "valor_liquido": calc['valor_liquido'],
                    "lucro": calc['taxa_total'],
                    "observacoes": f"Banco: {banco}, Cheque: {numero_cheque}. {observacoes}",
                    "data_vencimento": str(data_cheque),
                    "taxa_percentual": taxa_percentual_str
                }
                
                # Exibir simulação
                st.success(f"✅ **Simulação - {tipo_cheque}**")
                if "dias" in calc:
                    st.write(f"**Prazo:** {calc['dias']} dias")
                st.write(f"**Taxa Cliente ({taxa_percentual_str}):** R$ {calc['taxa_total']:.2f}")
                st.write(f"**💵 Valor a Entregar:** R$ {calc['valor_liquido']:.2f}")
            else:
                st.error("Não foi possível gerar a simulação. Verifique os dados (ex: prazo do cheque).")
        else:
            st.warning("O valor do cheque deve ser maior que zero.")
    
    # Formulário de confirmação
    with st.form(f"form_cheque_{tipo_cheque}", clear_on_submit=True):
        st.markdown("Clique em **Confirmar** para salvar a última operação simulada.")
        
        # Mostrar resumo da simulação atual
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
                    str(date.today()),
                    datetime.now().strftime("%H:%M:%S"),
                    st.session_state.nome_usuario,
                    simulacao['tipo_operacao'],
                    simulacao['cliente'] or "Não informado",
                    simulacao['cpf'] or "Não informado",
                    float(simulacao['valor_bruto']),
                    float(simulacao['taxa_cliente']),
                    float(simulacao['taxa_banco']),
                    float(simulacao['valor_liquido']),
                    float(simulacao['lucro']),
                    "Concluído",
                    simulacao['data_vencimento'],
                    simulacao['taxa_percentual'],
                    simulacao['observacoes']
                ]
                
                caixa_sheet.append_row(nova_operacao)
                st.success(f"✅ Operação registrada com sucesso!")
                st.session_state.simulacao_atual = None
                st.cache_data.clear()
            else:
                st.error("Nenhuma simulação válida encontrada. Por favor, clique em 'Simular Operação' primeiro.")

def render_form_suprimento(spreadsheet):
    st.markdown("### 💰 Suprimento do Caixa")
    
    HEADERS = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", 
               "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", 
               "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]
    
    with st.form("form_suprimento", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            valor = st.number_input("Valor do Suprimento (R$):", min_value=0.01, value=500.0, step=100.0)
            origem = st.selectbox("Origem do Suprimento:", ["Cofre Principal", "Depósito", "Outro"])
        
        with col2:
            observacoes = st.text_area("Observações:", height=100, placeholder="Informações adicionais sobre o suprimento...")
        
        # Resumo da operação
        st.markdown("#### 💰 Resumo da Operação")
        st.write(f"**💵 Valor a Adicionar:** R$ {valor:,.2f}")
        st.write(f"**📍 Origem:** {origem}")
        
        submitted = st.form_submit_button("💾 Confirmar Suprimento", use_container_width=True)
        
        if submitted:
            caixa_sheet = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", HEADERS)
            
            nova_operacao = [
                str(date.today()),
                datetime.now().strftime("%H:%M:%S"),
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
                f"Origem: {origem}. {observacoes}"
            ]
            
            caixa_sheet.append_row(nova_operacao)
            st.success("✅ Suprimento registrado com sucesso!")
            st.balloons()
            st.cache_data.clear()

def render_operacoes_caixa(spreadsheet):
    st.subheader("💸 Operações do Caixa Interno")
    
    tab1, tab2 = st.tabs(["➕ Nova Operação", "📋 Histórico"])
    
    with tab1:
        tipo_operacao = st.selectbox(
            "Selecione o Tipo de Operação:",
            ["Saque Cartão Débito", "Saque Cartão Crédito", "Cheque à Vista", 
             "Cheque Pré-datado", "Cheque com Taxa Manual", "Suprimento Caixa"],
            on_change=lambda: st.session_state.update(simulacao_atual=None)
        )
        
        if tipo_operacao == "Saque Cartão Débito":
            render_form_saque_cartao(spreadsheet, "Débito")
        elif tipo_operacao == "Saque Cartão Crédito":
            render_form_saque_cartao(spreadsheet, "Crédito")
        elif tipo_operacao == "Cheque à Vista":
            render_form_cheque(spreadsheet, "Cheque à Vista")
        elif tipo_operacao == "Cheque Pré-datado":
            render_form_cheque(spreadsheet, "Cheque Pré-datado")
        elif tipo_operacao == "Cheque com Taxa Manual":
            render_form_cheque(spreadsheet, "Cheque com Taxa Manual")
        elif tipo_operacao == "Suprimento Caixa":
            render_form_suprimento(spreadsheet)
    
    with tab2:
        try:
            HEADERS = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", 
                      "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", 
                      "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]
            
            data = buscar_dados(spreadsheet, "Operacoes_Caixa")
            
            if data:
                df = pd.DataFrame(data)
                
                # Garantir que todas as colunas existam
                for col in HEADERS:
                    if col not in df.columns:
                        df[col] = ''
                
                # Filtros
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    filtro_data = st.date_input("Filtrar por data:", value=None, key="filtro_data_hist")
                
                with col2:
                    tipos_unicos = df['Tipo_Operacao'].unique() if 'Tipo_Operacao' in df.columns else []
                    filtro_tipo = st.selectbox("Filtrar por tipo:", ["Todos"] + list(tipos_unicos))
                
                with col3:
                    filtro_operador = st.selectbox("Filtrar por operador:", 
                                                 ["Todos"] + list(df['Operador'].unique()) if 'Operador' in df.columns else ["Todos"])
                
                # Aplicar filtros
                df_filtrado = df.copy()
                
                if filtro_data and 'Data' in df.columns:
                    df_filtrado = df_filtrado[df_filtrado['Data'] == str(filtro_data)]
                
                if filtro_tipo != "Todos" and 'Tipo_Operacao' in df.columns:
                    df_filtrado = df_filtrado[df_filtrado['Tipo_Operacao'] == filtro_tipo]
                
                if filtro_operador != "Todos" and 'Operador' in df.columns:
                    df_filtrado = df_filtrado[df_filtrado['Operador'] == filtro_operador]
                
                # Exibir dados
                st.dataframe(df_filtrado, use_container_width=True)
                
                # Totais
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
# Sistema Principal
# ---------------------------
def sistema_principal():
    spreadsheet = conectar_google_sheets()
    
    if not spreadsheet:
        st.error("❌ Não foi possível conectar ao Google Sheets. Verifique as credenciais.")
        return
    
    # Sidebar com navegação
    st.sidebar.title("📋 Menu Principal")
    st.sidebar.success(f"✅ {st.session_state.nome_usuario}")
    st.sidebar.success("🌐 Conectado ao Google Sheets")
    st.sidebar.markdown("---")
    
    # Menu baseado no perfil
    if st.session_state.perfil_usuario == "gerente":
        st.sidebar.subheader("🏠 Dashboards")
        if st.sidebar.button("💳 Dashboard Caixa", use_container_width=True):
            st.session_state.pagina_atual = "dashboard_caixa"
            st.rerun()
        
        st.sidebar.subheader("💰 Operações")
        if st.sidebar.button("💸 Operações Caixa", use_container_width=True):
            st.session_state.pagina_atual = "operacoes_caixa"
            st.rerun()
    
    elif st.session_state.perfil_usuario == "operador_caixa":
        if st.sidebar.button("💳 Dashboard Caixa", use_container_width=True):
            st.session_state.pagina_atual = "dashboard_caixa"
            st.rerun()
        if st.sidebar.button("💸 Operações Caixa", use_container_width=True):
            st.session_state.pagina_atual = "operacoes_caixa"
            st.rerun()
    
    # Botão de logout
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        st.session_state.acesso_liberado = False
        st.session_state.simulacao_atual = None
        st.rerun()
    
    # Renderizar página atual
    pagina_atual = st.session_state.get('pagina_atual', 'dashboard_caixa')
    
    if pagina_atual == "dashboard_caixa":
        render_dashboard_caixa(spreadsheet)
    elif pagina_atual == "operacoes_caixa":
        render_operacoes_caixa(spreadsheet)

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

