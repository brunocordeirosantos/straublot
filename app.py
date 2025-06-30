import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
import os
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(
    page_title="Sistema Lotérica - Google Sheets",
    page_icon="🎰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------
# CSS Customizado para UX Melhorado
# ---------------------------
def load_custom_css():
    st.markdown("""
    <style>
    /* Importar fonte moderna */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Reset e configurações gerais */
    .main {
        font-family: 'Inter', sans-serif;
    }
    
    /* Botões maiores e mais atraentes */
    .stButton > button {
        height: 3.5rem;
        width: 100%;
        font-size: 1.1rem;
        font-weight: 500;
        border-radius: 12px;
        border: none;
        background: linear-gradient(135deg, #1E88E5 0%, #1565C0 100%);
        color: white;
        box-shadow: 0 4px 12px rgba(30, 136, 229, 0.3);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(30, 136, 229, 0.4);
        background: linear-gradient(135deg, #1565C0 0%, #0D47A1 100%);
    }
    
    /* Botões de ação específicos */
    .btn-success {
        background: linear-gradient(135deg, #43A047 0%, #2E7D32 100%) !important;
        box-shadow: 0 4px 12px rgba(67, 160, 71, 0.3) !important;
    }
    
    .btn-warning {
        background: linear-gradient(135deg, #FB8C00 0%, #E65100 100%) !important;
        box-shadow: 0 4px 12px rgba(251, 140, 0, 0.3) !important;
    }
    
    .btn-danger {
        background: linear-gradient(135deg, #E53935 0%, #C62828 100%) !important;
        box-shadow: 0 4px 12px rgba(229, 57, 53, 0.3) !important;
    }
    
    /* Inputs maiores e mais amigáveis */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select {
        height: 3rem;
        font-size: 1.1rem;
        border-radius: 8px;
        border: 2px solid #E0E0E0;
        transition: border-color 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #1E88E5;
        box-shadow: 0 0 0 3px rgba(30, 136, 229, 0.1);
    }
    
    /* Cards personalizados */
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        padding: 1.5rem;
        border-radius: 16px;
        border: 1px solid #E0E0E0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        margin: 0.5rem 0;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1E88E5;
        margin: 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #666;
        margin: 0;
        font-weight: 500;
    }
    
    /* Alertas melhorados */
    .alert-success {
        background: linear-gradient(135deg, #E8F5E8 0%, #C8E6C9 100%);
        border-left: 4px solid #43A047;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .alert-warning {
        background: linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%);
        border-left: 4px solid #FB8C00;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .alert-danger {
        background: linear-gradient(135deg, #FFEBEE 0%, #FFCDD2 100%);
        border-left: 4px solid #E53935;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    /* Sidebar melhorada */
    .css-1d391kg {
        background: linear-gradient(180deg, #1E88E5 0%, #1565C0 100%);
    }
    
    .css-1d391kg .css-1v0mbdj {
        color: white;
    }
    
    /* Responsividade mobile */
    @media (max-width: 768px) {
        .stButton > button {
            height: 4rem;
            font-size: 1.2rem;
        }
        
        .metric-card {
            padding: 1rem;
        }
        
        .metric-value {
            font-size: 1.5rem;
        }
        
        /* Ajustar colunas em mobile */
        .row-widget.stHorizontal {
            flex-direction: column;
        }
    }
    
    /* Animações suaves */
    .element-container {
        transition: all 0.3s ease;
    }
    
    /* Melhorar tabelas */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    /* Loading spinner customizado */
    .stSpinner {
        color: #1E88E5;
    }
    
    /* Tabs melhoradas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        padding: 0 1.5rem;
        border-radius: 8px;
        background: #F5F5F5;
        border: none;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1E88E5 0%, #1565C0 100%);
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------
# Componentes UI Customizados
# ---------------------------
def criar_card_metrica(titulo, valor, icone, cor="#1E88E5"):
    """Cria um card de métrica personalizado"""
    st.markdown(f"""
    <div class="metric-card">
        <p class="metric-label">{icone} {titulo}</p>
        <h2 class="metric-value" style="color: {cor};">{valor}</h2>
    </div>
    """, unsafe_allow_html=True)

def mostrar_alerta(tipo, mensagem):
    """Mostra alertas customizados"""
    if tipo == "success":
        st.markdown(f'<div class="alert-success">✅ {mensagem}</div>', unsafe_allow_html=True)
    elif tipo == "warning":
        st.markdown(f'<div class="alert-warning">⚠️ {mensagem}</div>', unsafe_allow_html=True)
    elif tipo == "error":
        st.markdown(f'<div class="alert-danger">❌ {mensagem}</div>', unsafe_allow_html=True)

def botao_acao(label, key, tipo="primary"):
    """Cria botões de ação customizados"""
    css_class = ""
    if tipo == "success":
        css_class = "btn-success"
    elif tipo == "warning":
        css_class = "btn-warning"
    elif tipo == "danger":
        css_class = "btn-danger"
    
    return st.button(label, key=key, use_container_width=True)

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
# Sistema de Acesso Melhorado
# ---------------------------
if 'acesso_liberado' not in st.session_state:
    st.session_state.acesso_liberado = False

def verificar_acesso():
    # Carregar CSS customizado
    load_custom_css()
    
    # Container centralizado
    st.markdown("<div style='text-align: center; padding: 2rem 0;'>", unsafe_allow_html=True)
    
    # Logo e título
    st.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <h1 style='color: #1E88E5; font-size: 3rem; margin-bottom: 0.5rem;'>🎰</h1>
        <h1 style='color: #333; margin-bottom: 0.5rem;'>Sistema de Gestão</h1>
        <h2 style='color: #666; font-weight: 400;'>Lotérica Google Sheets</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Formulário de login centralizado
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Acesso ao Sistema")
        
        with st.form("form_login", clear_on_submit=False):
            senha = st.text_input(
                "Digite a senha de acesso:", 
                type="password", 
                key="senha_acesso",
                placeholder="Digite sua senha..."
            )
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                login_btn = st.form_submit_button("🚀 Acessar Sistema")
            
            with col_btn2:
                ajuda_btn = st.form_submit_button("ℹ️ Ajuda")
            
            if login_btn:
                if senha == "loterica123":  # Senha padrão
                    st.session_state.acesso_liberado = True
                    mostrar_alerta("success", "Acesso liberado com sucesso!")
                    st.rerun()
                else:
                    mostrar_alerta("error", "Senha incorreta! Tente novamente.")
            
            if ajuda_btn:
                st.info("💡 **Senha padrão:** loterica123")
    
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------
# Sistema Principal Melhorado
# ---------------------------
def sistema_principal():
    # Carregar CSS customizado
    load_custom_css()
    
    # Inicializar Google Sheets
    client, spreadsheet = init_google_sheets()
    
    if not client or not spreadsheet:
        mostrar_alerta("error", "Não foi possível conectar ao Google Sheets. Verifique as credenciais.")
        return
    
    # Header melhorado
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown("""
        <div style='display: flex; align-items: center; margin-bottom: 1rem;'>
            <h1 style='color: #1E88E5; margin: 0; margin-right: 1rem;'>🏠</h1>
            <div>
                <h1 style='margin: 0; color: #333;'>Sistema de Gestão</h1>
                <p style='margin: 0; color: #666;'>Lotérica Google Sheets</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if st.button("🔄 Atualizar", use_container_width=True):
            st.rerun()
    
    with col3:
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.acesso_liberado = False
            st.rerun()
    
    # Sidebar melhorada
    with st.sidebar:
        st.markdown("""
        <div style='text-align: center; padding: 1rem 0; color: white;'>
            <h2 style='margin: 0; color: white;'>📋 Menu Principal</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Status de conexão
        mostrar_alerta("success", "Conectado ao Google Sheets")
        
        st.markdown("---")
        
        # Menu com ícones melhorados
        opcoes = [
            ("🏠", "Dashboard"),
            ("💰", "Lançamentos de Caixa"),
            ("🏦", "Gestão do Cofre"), 
            ("📦", "Gestão de Estoque"),
            ("📊", "Relatórios"),
            ("⚙️", "Configurações")
        ]
        
        opcao_selecionada = st.radio(
            "Escolha uma opção:",
            [f"{icone} {nome}" for icone, nome in opcoes],
            label_visibility="collapsed"
        )
    
    # Renderizar página baseada na seleção
    if "Dashboard" in opcao_selecionada:
        render_dashboard_melhorado(spreadsheet)
    elif "Lançamentos" in opcao_selecionada:
        render_lancamentos_melhorado(spreadsheet)
    elif "Cofre" in opcao_selecionada:
        render_cofre_melhorado(spreadsheet)
    elif "Estoque" in opcao_selecionada:
        render_estoque_melhorado(spreadsheet)
    elif "Relatórios" in opcao_selecionada:
        render_relatorios_melhorado(spreadsheet)
    elif "Configurações" in opcao_selecionada:
        render_configuracoes_melhorado()

# ---------------------------
# Dashboard Melhorado
# ---------------------------
def render_dashboard_melhorado(spreadsheet):
    st.markdown("## 🏠 Dashboard")
    
    try:
        # Carregar dados
        lancamentos_sheet = get_or_create_worksheet(
            spreadsheet, 
            "Lançamentos Caixa",
            ["Data", "Hora", "PDV", "Tipo", "Produto", "Quantidade", "Valor", "Observações"]
        )
        
        cofre_sheet = get_or_create_worksheet(
            spreadsheet,
            "Cofre",
            ["Data", "Hora", "Tipo", "Valor", "Saldo", "Descrição"]
        )
        
        # Obter dados
        lancamentos_data = lancamentos_sheet.get_all_records()
        cofre_data = cofre_sheet.get_all_records()
        
        # Cards de métricas melhorados
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            saldo_cofre = cofre_data[-1]["Saldo"] if cofre_data else 1000.0
            criar_card_metrica("Saldo do Cofre", f"R$ {saldo_cofre:.2f}", "💰", "#43A047")
        
        with col2:
            vendas_hoje = sum([float(l["Valor"]) for l in lancamentos_data 
                              if l["Data"] == str(date.today()) and l["Tipo"] == "venda"])
            criar_card_metrica("Vendas Hoje", f"R$ {vendas_hoje:.2f}", "📈", "#1E88E5")
        
        with col3:
            total_movimentacoes = len([l for l in lancamentos_data 
                                     if l["Data"] == str(date.today())])
            criar_card_metrica("Movimentações", f"{total_movimentacoes}", "📋", "#FB8C00")
        
        with col4:
            criar_card_metrica("Status", "Online", "🌐", "#43A047")
        
        st.markdown("---")
        
        # Botões de ação rápida
        st.markdown("### ⚡ Ações Rápidas")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if botao_acao("🎯 Venda Rápida", "venda_rapida", "success"):
                st.session_state.acao_rapida = "venda"
        
        with col2:
            if botao_acao("💰 Suprimento", "suprimento", "primary"):
                st.session_state.acao_rapida = "suprimento"
        
        with col3:
            if botao_acao("📤 Sangria", "sangria", "warning"):
                st.session_state.acao_rapida = "sangria"
        
        with col4:
            if botao_acao("📊 Relatório", "relatorio", "primary"):
                st.session_state.acao_rapida = "relatorio"
        
        st.markdown("---")
        
        # Gráfico de vendas melhorado
        if lancamentos_data:
            st.markdown("### 📊 Vendas dos Últimos 7 Dias")
            
            vendas_por_dia = {}
            for lancamento in lancamentos_data:
                if lancamento["Tipo"] == "venda":
                    data = lancamento["Data"]
                    if data not in vendas_por_dia:
                        vendas_por_dia[data] = 0
                    vendas_por_dia[data] += float(lancamento["Valor"])
            
            if vendas_por_dia:
                df_vendas = pd.DataFrame(list(vendas_por_dia.items()), columns=["Data", "Vendas"])
                
                fig = px.line(
                    df_vendas, 
                    x="Data", 
                    y="Vendas", 
                    title="📈 Evolução das Vendas",
                    color_discrete_sequence=["#1E88E5"]
                )
                
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font_family="Inter",
                    title_font_size=20,
                    title_font_color="#333"
                )
                
                st.plotly_chart(fig, use_container_width=True)
        
        # Alertas e notificações
        st.markdown("### 🔔 Alertas e Notificações")
        
        # Verificar alertas
        alertas = verificar_alertas(cofre_data, lancamentos_data)
        
        if alertas:
            for alerta in alertas:
                mostrar_alerta(alerta["tipo"], alerta["mensagem"])
        else:
            mostrar_alerta("success", "Tudo funcionando perfeitamente!")
        
    except Exception as e:
        mostrar_alerta("error", f"Erro ao carregar dashboard: {e}")

def verificar_alertas(cofre_data, lancamentos_data):
    """Verifica e retorna alertas do sistema"""
    alertas = []
    
    # Verificar saldo baixo
    if cofre_data:
        saldo_atual = float(cofre_data[-1]["Saldo"])
        if saldo_atual < 500:
            alertas.append({
                "tipo": "warning",
                "mensagem": f"Saldo do cofre baixo: R$ {saldo_atual:.2f}"
            })
    
    # Verificar movimentações do dia
    hoje = str(date.today())
    movs_hoje = len([l for l in lancamentos_data if l["Data"] == hoje])
    
    if movs_hoje == 0:
        alertas.append({
            "tipo": "warning",
            "mensagem": "Nenhuma movimentação registrada hoje"
        })
    
    return alertas

# ---------------------------
# Lançamentos Melhorados
# ---------------------------
def render_lancamentos_melhorado(spreadsheet):
    st.markdown("## 💰 Lançamentos de Caixa")
    
    try:
        # Obter worksheet
        sheet = get_or_create_worksheet(
            spreadsheet,
            "Lançamentos Caixa",
            ["Data", "Hora", "PDV", "Tipo", "Produto", "Quantidade", "Valor", "Observações"]
        )
        
        tab1, tab2 = st.tabs(["➕ Novo Lançamento", "📋 Histórico"])
        
        with tab1:
            st.markdown("#### ✨ Registrar Nova Movimentação")
            
            # Formulário melhorado
            with st.form("formulario_lancamento_melhorado", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    pdv = st.selectbox(
                        "🏪 PDV:", 
                        ["PDV 1", "PDV 2", "PDV 3"],
                        help="Selecione o ponto de venda"
                    )
                    
                    tipo = st.selectbox(
                        "📝 Tipo de Movimentação:", 
                        ["venda", "suprimento", "sangria", "vale", "pagamento_premio"],
                        help="Escolha o tipo de operação"
                    )
                    
                    if tipo == "venda":
                        produto = st.selectbox(
                            "🎯 Produto:", 
                            ["bolao", "raspadinha", "loteria_federal"],
                            help="Selecione o produto vendido"
                        )
                        quantidade = st.number_input(
                            "📦 Quantidade:", 
                            min_value=1, 
                            value=1,
                            help="Quantidade de produtos"
                        )
                        
                        # Preços padrão com visual melhorado
                        precos = {"bolao": 5.0, "raspadinha": 2.0, "loteria_federal": 10.0}
                        valor = quantidade * precos[produto]
                        
                        st.markdown(f"""
                        <div class="metric-card">
                            <p class="metric-label">💰 Valor Total</p>
                            <h2 class="metric-value">R$ {valor:.2f}</h2>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        produto = ""
                        quantidade = 0
                        valor = st.number_input(
                            "💵 Valor (R$):", 
                            min_value=0.01, 
                            value=10.0, 
                            step=0.01,
                            help="Digite o valor da operação"
                        )
                
                with col2:
                    observacoes = st.text_area(
                        "📝 Observações:", 
                        height=150,
                        placeholder="Digite observações adicionais...",
                        help="Informações extras sobre a operação"
                    )
                
                # Botão de envio melhorado
                col_enviar = st.columns([2, 1, 2])[1]
                with col_enviar:
                    enviar = st.form_submit_button("💾 Registrar Lançamento")
                
                if enviar:
                    # Preparar dados
                    nova_linha = [
                        str(date.today()),
                        datetime.now().strftime("%H:%M:%S"),
                        pdv,
                        tipo,
                        produto,
                        quantidade,
                        valor,
                        observacoes
                    ]
                    
                    # Salvar no Google Sheets
                    sheet.append_row(nova_linha)
                    
                    # Atualizar cofre se for venda
                    if tipo == "venda":
                        atualizar_cofre(spreadsheet, valor, f"Venda {produto}")
                    
                    mostrar_alerta("success", "Lançamento salvo no Google Sheets com sucesso!")
                    st.rerun()
        
        with tab2:
            st.markdown("#### 📋 Histórico de Lançamentos")
            
            # Carregar dados
            data = sheet.get_all_records()
            
            if data:
                df = pd.DataFrame(data)
                
                # Filtros
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    filtro_data = st.date_input("📅 Filtrar por data:", value=date.today())
                
                with col2:
                    tipos_unicos = df["Tipo"].unique() if not df.empty else []
                    filtro_tipo = st.selectbox("📝 Filtrar por tipo:", ["Todos"] + list(tipos_unicos))
                
                with col3:
                    pdvs_unicos = df["PDV"].unique() if not df.empty else []
                    filtro_pdv = st.selectbox("🏪 Filtrar por PDV:", ["Todos"] + list(pdvs_unicos))
                
                # Aplicar filtros
                df_filtrado = df.copy()
                
                if filtro_data:
                    df_filtrado = df_filtrado[df_filtrado["Data"] == str(filtro_data)]
                
                if filtro_tipo != "Todos":
                    df_filtrado = df_filtrado[df_filtrado["Tipo"] == filtro_tipo]
                
                if filtro_pdv != "Todos":
                    df_filtrado = df_filtrado[df_filtrado["PDV"] == filtro_pdv]
                
                # Mostrar dados filtrados
                if not df_filtrado.empty:
                    st.dataframe(df_filtrado, use_container_width=True)
                    
                    # Resumo
                    total_valor = df_filtrado["Valor"].astype(float).sum()
                    st.markdown(f"**Total filtrado: R$ {total_valor:.2f}**")
                else:
                    st.info("📋 Nenhum lançamento encontrado com os filtros aplicados.")
            else:
                st.info("📋 Nenhum lançamento registrado ainda.")
                
    except Exception as e:
        mostrar_alerta("error", f"Erro ao processar lançamentos: {e}")

# ---------------------------
# Outras funções melhoradas (simplificadas para o exemplo)
# ---------------------------
def render_cofre_melhorado(spreadsheet):
    st.markdown("## 🏦 Gestão do Cofre")
    st.info("🚧 Interface melhorada em desenvolvimento...")

def render_estoque_melhorado(spreadsheet):
    st.markdown("## 📦 Gestão de Estoque")
    st.info("🚧 Interface melhorada em desenvolvimento...")

def render_relatorios_melhorado(spreadsheet):
    st.markdown("## 📊 Relatórios")
    st.info("🚧 Interface melhorada em desenvolvimento...")

def render_configuracoes_melhorado():
    st.markdown("## ⚙️ Configurações")
    st.info("🚧 Interface melhorada em desenvolvimento...")

# Função auxiliar para atualizar cofre (mantida igual)
def atualizar_cofre(spreadsheet, valor, descricao):
    """Atualiza saldo do cofre"""
    try:
        cofre_sheet = get_or_create_worksheet(
            spreadsheet,
            "Cofre", 
            ["Data", "Hora", "Tipo", "Valor", "Saldo", "Descrição"]
        )
        
        # Obter saldo atual
        cofre_data = cofre_sheet.get_all_records()
        saldo_atual = float(cofre_data[-1]["Saldo"]) if cofre_data else 1000.0
        
        # Calcular novo saldo
        novo_saldo = saldo_atual + valor
        
        # Salvar movimentação
        nova_linha = [
            str(date.today()),
            datetime.now().strftime("%H:%M:%S"),
            "entrada",
            valor,
            novo_saldo,
            descricao
        ]
        
        cofre_sheet.append_row(nova_linha)
        
    except Exception as e:
        mostrar_alerta("error", f"Erro ao atualizar cofre: {e}")

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

