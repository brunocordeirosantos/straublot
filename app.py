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
        "valor_liquido": valor_liquido,
        "tipo": "Débito"
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
        "valor_liquido": valor_liquido,
        "tipo": "Crédito"
    }

def calcular_taxa_cheque(valor, data_cheque):
    """Calcula taxa para troca de cheque"""
    hoje = date.today()
    data_venc = datetime.strptime(data_cheque, "%Y-%m-%d").date()
    
    # Taxa base de 2%
    taxa_base = valor * 0.02
    
    # Se for pré-datado, adicionar taxa diária
    if data_venc > hoje:
        dias = (data_venc - hoje).days
        if dias > 15:  # Limite máximo de 15 dias
            return None
        taxa_diaria = valor * 0.0033 * dias  # 0.33% por dia
    else:
        taxa_diaria = 0
    
    taxa_total = taxa_base + taxa_diaria
    valor_liquido = valor - taxa_total
    
    return {
        "taxa_base": taxa_base,
        "taxa_diaria": taxa_diaria,
        "taxa_total": taxa_total,
        "valor_liquido": valor_liquido,
        "dias": (data_venc - hoje).days if data_venc > hoje else 0
    }

# ---------------------------
# Sistema Principal
# ---------------------------
def sistema_principal():
    # Inicializar Google Sheets
    client, spreadsheet = init_google_sheets()
    
    if not client or not spreadsheet:
        st.error("❌ Não foi possível conectar ao Google Sheets. Verifique as credenciais.")
        return
    
    # Header personalizado por perfil
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
    
    # Sidebar com menu baseado no perfil
    st.sidebar.title("📋 Menu Principal")
    st.sidebar.success(f"✅ {st.session_state.nome_usuario}")
    st.sidebar.success("🌐 Conectado ao Google Sheets")
    st.sidebar.markdown("---")
    
    # Menu dinâmico baseado no perfil - botões diretos
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
    
    # Definir página padrão se não existir
    if 'pagina_atual' not in st.session_state:
        if st.session_state.perfil_usuario == "operador_caixa":
            st.session_state.pagina_atual = "dashboard_caixa"
        elif st.session_state.perfil_usuario == "operador_loterica":
            st.session_state.pagina_atual = "dashboard_loterica"
        else:
            st.session_state.pagina_atual = "dashboard_caixa"
    
    # Renderizar página baseada na seleção
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
             "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", "Observacoes"]
        )
        
        # Obter dados
        operacoes_data = caixa_sheet.get_all_records()
        
        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        
        # Calcular saldo atual considerando TODAS as operações
        saldo_caixa = 5000.0  # Valor inicial do caixa
        valor_saque_hoje = 0
        operacoes_hoje = 0
        
        hoje_str = str(date.today())
        
        # Calcular saldo considerando TODAS as operações
        saldo_inicial = 5000.0  # Valor inicial do caixa
        total_suprimentos = 0
        total_saques_liquidos = 0
        
        # Debug: vamos calcular separadamente para entender
        for op in operacoes_data:
            try:
                if op["Tipo_Operacao"] == "Suprimento":
                    valor = float(op["Valor_Bruto"]) if op["Valor_Bruto"] else 0
                    total_suprimentos += valor
                elif op["Tipo_Operacao"] in ["Saque Cartão Débito", "Saque Cartão Crédito"]:
                    valor = float(op["Valor_Liquido"]) if op["Valor_Liquido"] else 0
                    total_saques_liquidos += valor
                elif op["Tipo_Operacao"] == "Troca Cheque":
                    valor = float(op["Valor_Liquido"]) if op["Valor_Liquido"] else 0
                    total_saques_liquidos += valor
            except (ValueError, TypeError):
                continue  # Pular valores inválidos
        
        # Cálculo final do saldo
        saldo_caixa = saldo_inicial + total_suprimentos - total_saques_liquidos
        
        # Contar operações de hoje para métricas
        for op in operacoes_data:
            if op["Data"] == hoje_str:
                operacoes_hoje += 1
                if op["Tipo_Operacao"] in ["Saque Cartão Débito", "Saque Cartão Crédito"]:
                    try:
                        valor_saque_hoje += float(op["Valor_Bruto"]) if op["Valor_Bruto"] else 0
                    except (ValueError, TypeError):
                        continue
        
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
                <h3>{operacoes_hoje}</h3>
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
        if operacoes_data:
            st.subheader("📊 Operações dos Últimos 7 Dias")
            
            # Preparar dados para gráfico
            df_ops = pd.DataFrame(operacoes_data)
            if not df_ops.empty:
                # Filtrar últimos 7 dias
                df_ops['Data'] = pd.to_datetime(df_ops['Data'])
                data_limite = datetime.now() - timedelta(days=7)
                df_recente = df_ops[df_ops['Data'] >= data_limite]
                
                if not df_recente.empty:
                    # Agrupar por tipo de operação
                    ops_por_tipo = df_recente.groupby('Tipo_Operacao').size().reset_index(name='Quantidade')
                    
                    fig = px.pie(ops_por_tipo, values='Quantidade', names='Tipo_Operacao', 
                               title="Distribuição de Operações")
                    st.plotly_chart(fig, use_container_width=True)
        
        # Alertas
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

# ---------------------------
# Formulários de Operação
# ---------------------------
def render_form_saque_cartao(spreadsheet):
    st.markdown("### 💳 Saque Cartão")
    
    # Campos fora do form para permitir simulação
    col1, col2 = st.columns(2)
    
    with col1:
        cliente = st.text_input("Nome do Cliente (opcional):", placeholder="Digite o nome completo")
        cpf = st.text_input("CPF (opcional):", placeholder="000.000.000-00")
        valor = st.number_input("Valor do Saque (R$):", min_value=10.0, max_value=5000.0, value=100.0, step=10.0)
        tipo_cartao = st.selectbox("Tipo de Cartão:", ["Débito", "Crédito"])
    
    with col2:
        observacoes = st.text_area("Observações:", height=100, placeholder="Informações adicionais...")
        
        # Botão de simulação
        if st.button("🧮 Simular Operação", use_container_width=True):
            if valor > 0:
                if tipo_cartao == "Débito":
                    calc = calcular_taxa_cartao_debito(valor)
                    st.success("✅ **Simulação - Cartão Débito**")
                    st.write(f"**Taxa Cliente (1%):** R$ {calc['taxa_cliente']:.2f}")
                else:
                    calc = calcular_taxa_cartao_credito(valor)
                    st.success("✅ **Simulação - Cartão Crédito**")
                    st.write(f"**Taxa Cliente (5,33%):** R$ {calc['taxa_cliente']:.2f}")
                
                st.write(f"**💵 Valor a Entregar:** R$ {calc['valor_liquido']:.2f}")
                st.write(f"**💰 Taxa que fica no caixa:** R$ {calc['taxa_cliente']:.2f}")
    
    # Formulário para confirmação
    with st.form("form_saque_cartao"):
        st.markdown("#### 💾 Confirmar e Salvar Operação")
        
        # Mostrar resumo novamente
        if valor > 0:
            if tipo_cartao == "Débito":
                calc = calcular_taxa_cartao_debito(valor)
                st.info(f"**Resumo:** Taxa R$ {calc['taxa_cliente']:.2f} | Entregar R$ {calc['valor_liquido']:.2f}")
            else:
                calc = calcular_taxa_cartao_credito(valor)
                st.info(f"**Resumo:** Taxa R$ {calc['taxa_cliente']:.2f} | Entregar R$ {calc['valor_liquido']:.2f}")
        
        submitted = st.form_submit_button("💾 Confirmar e Salvar", use_container_width=True)
        
        if submitted:
            # Calcular baseado no tipo
            if tipo_cartao == "Débito":
                calc = calcular_taxa_cartao_debito(valor)
            else:
                calc = calcular_taxa_cartao_credito(valor)
            
            caixa_sheet = get_or_create_worksheet(
                spreadsheet,
                "Operacoes_Caixa",
                ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", 
                 "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", "Observacoes"]
            )
            
            # Data e hora automáticas
            data_atual = str(date.today())
            hora_atual = datetime.now().strftime("%H:%M:%S")
            
            nova_operacao = [
                data_atual,
                hora_atual,
                st.session_state.nome_usuario,
                f"Saque Cartão {tipo_cartao}",
                cliente if cliente else "Não informado",
                cpf if cpf else "Não informado",
                valor,
                calc['taxa_cliente'],
                calc['taxa_banco'],
                calc['valor_liquido'],
                calc['lucro'],
                "Concluído",
                observacoes
            ]
            
            caixa_sheet.append_row(nova_operacao)
            
            st.success("✅ Operação registrada com sucesso!")
            st.balloons()
            
            # Limpar ação rápida
            if hasattr(st.session_state, 'acao_rapida'):
                del st.session_state.acao_rapida
            
            st.rerun()

def render_form_troca_cheque(spreadsheet):
    st.markdown("### 📄 Troca de Cheque")
    
    # Campos fora do form para permitir simulação
    col1, col2 = st.columns(2)
    
    with col1:
        cliente = st.text_input("Nome do Cliente (opcional):", placeholder="Digite o nome completo")
        cpf = st.text_input("CPF (opcional):", placeholder="000.000.000-00")
        valor = st.number_input("Valor do Cheque (R$):", min_value=50.0, max_value=50000.0, value=1000.0, step=50.0)
        data_cheque = st.date_input("Data do Cheque:", value=date.today())
    
    with col2:
        banco = st.text_input("Banco:", placeholder="Nome do banco")
        numero_cheque = st.text_input("Número do Cheque:", placeholder="000000")
        observacoes = st.text_area("Observações:", height=100)
        
        # Botão de simulação
        if st.button("🧮 Simular Operação", use_container_width=True):
            if valor > 0:
                calc = calcular_taxa_cheque(valor, str(data_cheque))
                if calc:
                    st.success("✅ **Simulação - Troca de Cheque**")
                    st.write(f"**Taxa Total:** R$ {calc['taxa_total']:.2f}")
                    if calc['dias'] > 0:
                        st.write(f"**Dias até vencimento:** {calc['dias']}")
                    st.write(f"**💵 Valor a Entregar:** R$ {calc['valor_liquido']:.2f}")
                    st.write(f"**💰 Taxa que fica no caixa:** R$ {calc['taxa_total']:.2f}")
                else:
                    st.error("❌ Prazo máximo de 15 dias excedido!")
    
    # Formulário para confirmação
    with st.form("form_troca_cheque"):
        st.markdown("#### 💾 Confirmar e Salvar Operação")
        
        # Mostrar resumo novamente
        if valor > 0:
            calc = calcular_taxa_cheque(valor, str(data_cheque))
            if calc:
                st.info(f"**Resumo:** Taxa R$ {calc['taxa_total']:.2f} | Entregar R$ {calc['valor_liquido']:.2f}")
            else:
                st.error("❌ Prazo máximo de 15 dias excedido!")
        
        submitted = st.form_submit_button("💾 Confirmar e Salvar", use_container_width=True)
        
        if submitted:
            calc = calcular_taxa_cheque(valor, str(data_cheque))
            if not calc:
                st.error("❌ Prazo máximo de 15 dias excedido!")
            else:
                # Salvar operação
                caixa_sheet = get_or_create_worksheet(
                    spreadsheet,
                    "Operacoes_Caixa",
                    ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", 
                     "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", "Observacoes"]
                )
                
                # Data e hora automáticas
                data_atual = str(date.today())
                hora_atual = datetime.now().strftime("%H:%M:%S")
                
                nova_operacao = [
                    data_atual,
                    hora_atual,
                    st.session_state.nome_usuario,
                    "Troca Cheque",
                    cliente if cliente else "Não informado",
                    cpf if cpf else "Não informado",
                    valor,
                    calc['taxa_total'],
                    0,  # Sem taxa banco para cheques
                    calc['valor_liquido'],
                    calc['taxa_total'],  # Todo valor da taxa é lucro
                    "Concluído",
                    f"Banco: {banco}, Cheque: {numero_cheque}, Data: {data_cheque}. {observacoes}"
                ]
                
                caixa_sheet.append_row(nova_operacao)
                
                st.success("✅ Operação registrada com sucesso!")
                st.balloons()
                
                # Limpar ação rápida
                if hasattr(st.session_state, 'acao_rapida'):
                    del st.session_state.acao_rapida
                
                st.rerun()

# ---------------------------
# Operações do Caixa Interno
# ---------------------------
def render_operacoes_caixa(spreadsheet):
    st.subheader("💸 Operações do Caixa Interno")
    
    tab1, tab2 = st.tabs(["➕ Nova Operação", "📋 Histórico"])
    
    with tab1:
        tipo_operacao = st.selectbox(
            "Tipo de Operação:",
            ["Saque Cartão (Débito/Crédito)", "Troca Cheque", "Suprimento Caixa"]
        )
        
        if tipo_operacao == "Saque Cartão (Débito/Crédito)":
            render_form_saque_cartao(spreadsheet)
        elif tipo_operacao == "Troca Cheque":
            render_form_troca_cheque(spreadsheet)
        elif tipo_operacao == "Suprimento Caixa":
            render_form_suprimento(spreadsheet)
    
    with tab2:
        try:
            caixa_sheet = spreadsheet.worksheet("Operacoes_Caixa")
            data = caixa_sheet.get_all_records()
            
            if data:
                df = pd.DataFrame(data)
                
                # Filtros
                col1, col2, col3 = st.columns(3)
                with col1:
                    filtro_data = st.date_input("Filtrar por data:", value=date.today())
                with col2:
                    tipos_unicos = df['Tipo_Operacao'].unique() if 'Tipo_Operacao' in df.columns else []
                    filtro_tipo = st.selectbox("Filtrar por tipo:", ["Todos"] + list(tipos_unicos))
                with col3:
                    filtro_operador = st.selectbox("Filtrar por operador:", 
                                                 ["Todos"] + list(df['Operador'].unique()) if 'Operador' in df.columns else ["Todos"])
                
                # Aplicar filtros
                df_filtrado = df.copy()
                if 'Data' in df.columns:
                    df_filtrado = df_filtrado[df_filtrado['Data'] == str(filtro_data)]
                if filtro_tipo != "Todos" and 'Tipo_Operacao' in df.columns:
                    df_filtrado = df_filtrado[df_filtrado['Tipo_Operacao'] == filtro_tipo]
                if filtro_operador != "Todos" and 'Operador' in df.columns:
                    df_filtrado = df_filtrado[df_filtrado['Operador'] == filtro_operador]
                
                st.dataframe(df_filtrado, use_container_width=True)
                
                # Totais
                if not df_filtrado.empty and 'Valor_Bruto' in df_filtrado.columns:
                    total_operacoes = len(df_filtrado)
                    total_valor = df_filtrado['Valor_Bruto'].astype(float).sum()
                    total_lucro = df_filtrado['Lucro'].astype(float).sum() if 'Lucro' in df_filtrado.columns else 0
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total de Operações", total_operacoes)
                    with col2:
                        st.metric("Valor Total", f"R$ {total_valor:,.2f}")
                    with col3:
                        st.metric("Lucro Total", f"R$ {total_lucro:,.2f}")
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
    
    # Verificar se é gerente
    if st.session_state.perfil_usuario != "gerente":
        st.error("❌ Apenas o gerente pode realizar suprimentos do cofre!")
        return
    
    with st.form("form_suprimento"):
        col1, col2 = st.columns(2)
        
        with col1:
            valor_suprimento = st.number_input("Valor do Suprimento (R$):", min_value=50.0, max_value=10000.0, value=500.0, step=50.0)
            origem = st.selectbox("Origem do Suprimento:", ["Cofre Principal", "Depósito Bancário", "Outro"])
            
        with col2:
            observacoes = st.text_area("Observações:", height=100, placeholder="Motivo do suprimento, autorização, etc...")
            
            # Resumo da operação
            if valor_suprimento > 0:
                st.markdown("#### 💰 Resumo da Operação")
                st.write(f"**💵 Valor a Adicionar:** R$ {valor_suprimento:.2f}")
                st.write(f"**📍 Origem:** {origem}")
        
        submitted = st.form_submit_button("💾 Confirmar Suprimento", use_container_width=True)
        
        if submitted:
            # Salvar operação de suprimento
            caixa_sheet = get_or_create_worksheet(
                spreadsheet,
                "Operacoes_Caixa",
                ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", 
                 "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", "Observacoes"]
            )
            
            # Data e hora automáticas
            data_atual = str(date.today())
            hora_atual = datetime.now().strftime("%H:%M:%S")
            
            nova_operacao = [
                data_atual,
                hora_atual,
                st.session_state.nome_usuario,
                "Suprimento",
                "Sistema",
                "N/A",
                valor_suprimento,
                0,  # Sem taxa cliente
                0,  # Sem taxa banco
                valor_suprimento,  # Valor líquido = valor bruto
                0,  # Sem lucro em suprimento
                "Concluído",
                f"Origem: {origem}. {observacoes}"
            ]
            
            caixa_sheet.append_row(nova_operacao)
            
            st.success("✅ Suprimento registrado com sucesso!")
            st.balloons()
            
            # Limpar ação rápida
            if hasattr(st.session_state, 'acao_rapida'):
                del st.session_state.acao_rapida
            
            st.rerun()

def render_relatorio_rapido(operacoes_data):
    st.markdown("### 📊 Relatório Rápido - Hoje")
    
    hoje_str = str(date.today())
    ops_hoje = [op for op in operacoes_data if op.get("Data") == hoje_str]
    
    if ops_hoje:
        df = pd.DataFrame(ops_hoje)
        st.dataframe(df, use_container_width=True)
        
        # Totais
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
# Função Principal
# ---------------------------
def main():
    if not st.session_state.acesso_liberado:
        verificar_acesso()
    else:
        sistema_principal()

if __name__ == "__main__":
    main()

