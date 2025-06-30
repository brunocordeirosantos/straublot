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
# Configuração Google Sheets
# ---------------------------
@st.cache_resource
def init_google_sheets():
    """Inicializa conexão com Google Sheets"""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Carrega credenciais
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
# Sistema de Acesso Simples
# ---------------------------
if 'acesso_liberado' not in st.session_state:
    st.session_state.acesso_liberado = False

def verificar_acesso():
    st.title("🎰 Sistema de Gestão - Lotérica (Google Sheets)")
    st.markdown("### 🔐 Acesso ao Sistema")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        senha = st.text_input("Digite a senha de acesso:", type="password", key="senha_acesso")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🚀 Acessar Sistema", use_container_width=True):
                if senha == "loterica123":  # Senha padrão
                    st.session_state.acesso_liberado = True
                    st.success("✅ Acesso liberado!")
                    st.rerun()
                else:
                    st.error("❌ Senha incorreta!")
        
        with col_btn2:
            if st.button("ℹ️ Ajuda", use_container_width=True):
                st.info("💡 Senha padrão: **loterica123**")

# ---------------------------
# Sistema Principal
# ---------------------------
def sistema_principal():
    # Inicializar Google Sheets
    client, spreadsheet = init_google_sheets()
    
    if not client or not spreadsheet:
        st.error("❌ Não foi possível conectar ao Google Sheets. Verifique as credenciais.")
        return
    
    # Header
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("🏠 Sistema de Gestão - Lotérica (Google Sheets)")
    with col2:
        if st.button("🚪 Sair"):
            st.session_state.acesso_liberado = False
            st.rerun()
    
    # Sidebar com menu
    st.sidebar.title("📋 Menu Principal")
    st.sidebar.success("✅ Conectado ao Google Sheets")
    st.sidebar.markdown("---")
    
    opcao = st.sidebar.selectbox(
        "Escolha uma opção:",
        [
            "🏠 Dashboard",
            "💰 Lançamentos de Caixa",
            "🏦 Gestão do Cofre", 
            "📦 Gestão de Estoque",
            "📊 Relatórios",
            "⚙️ Configurações"
        ]
    )
    
    # Renderizar página baseada na seleção
    if opcao == "🏠 Dashboard":
        render_dashboard(spreadsheet)
    elif opcao == "💰 Lançamentos de Caixa":
        render_lancamentos(spreadsheet)
    elif opcao == "🏦 Gestão do Cofre":
        render_cofre(spreadsheet)
    elif opcao == "📦 Gestão de Estoque":
        render_estoque(spreadsheet)
    elif opcao == "📊 Relatórios":
        render_relatorios(spreadsheet)
    elif opcao == "⚙️ Configurações":
        render_configuracoes()

# ---------------------------
# Dashboard
# ---------------------------
def render_dashboard(spreadsheet):
    st.subheader("🏠 Dashboard")
    
    try:
        # Carregar dados dos lançamentos
        lancamentos_sheet = get_or_create_worksheet(
            spreadsheet, 
            "Lançamentos Caixa",
            ["Data", "Hora", "PDV", "Tipo", "Produto", "Quantidade", "Valor", "Observações"]
        )
        
        # Carregar dados do cofre
        cofre_sheet = get_or_create_worksheet(
            spreadsheet,
            "Cofre",
            ["Data", "Hora", "Tipo", "Valor", "Saldo", "Descrição"]
        )
        
        # Obter dados
        lancamentos_data = lancamentos_sheet.get_all_records()
        cofre_data = cofre_sheet.get_all_records()
        
        # Calcular métricas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            saldo_cofre = cofre_data[-1]["Saldo"] if cofre_data else 1000.0
            st.metric("💰 Saldo do Cofre", f"R$ {saldo_cofre:.2f}")
        
        with col2:
            vendas_hoje = sum([float(l["Valor"]) for l in lancamentos_data 
                              if l["Data"] == str(date.today()) and l["Tipo"] == "venda"])
            st.metric("📈 Vendas Hoje", f"R$ {vendas_hoje:.2f}")
        
        with col3:
            total_movimentacoes = len([l for l in lancamentos_data 
                                     if l["Data"] == str(date.today())])
            st.metric("📋 Movimentações Hoje", f"{total_movimentacoes}")
        
        with col4:
            st.metric("🌐 Status", "Online")
        
        st.markdown("---")
        
        # Gráfico de vendas
        if lancamentos_data:
            st.subheader("📊 Vendas dos Últimos 7 Dias")
            
            vendas_por_dia = {}
            for lancamento in lancamentos_data:
                if lancamento["Tipo"] == "venda":
                    data = lancamento["Data"]
                    if data not in vendas_por_dia:
                        vendas_por_dia[data] = 0
                    vendas_por_dia[data] += float(lancamento["Valor"])
            
            if vendas_por_dia:
                df_vendas = pd.DataFrame(list(vendas_por_dia.items()), columns=["Data", "Vendas"])
                fig = px.line(df_vendas, x="Data", y="Vendas", title="Evolução das Vendas")
                st.plotly_chart(fig, use_container_width=True)
        
        st.success("✅ **Sistema integrado com Google Sheets funcionando!**")
        
    except Exception as e:
        st.error(f"Erro ao carregar dashboard: {e}")

# ---------------------------
# Lançamentos de Caixa
# ---------------------------
def render_lancamentos(spreadsheet):
    st.subheader("💰 Lançamentos de Caixa")
    
    try:
        # Obter worksheet
        sheet = get_or_create_worksheet(
            spreadsheet,
            "Lançamentos Caixa",
            ["Data", "Hora", "PDV", "Tipo", "Produto", "Quantidade", "Valor", "Observações"]
        )
        
        tab1, tab2 = st.tabs(["➕ Novo Lançamento", "📋 Histórico"])
        
        with tab1:
            st.markdown("#### Registrar Nova Movimentação")
            
            with st.form("formulario_lancamento"):
                col1, col2 = st.columns(2)
                
                with col1:
                    pdv = st.selectbox("PDV:", ["PDV 1", "PDV 2", "PDV 3"])
                    tipo = st.selectbox("Tipo de Movimentação:", [
                        "venda", "suprimento", "sangria", "vale", "pagamento_premio"
                    ])
                    
                    if tipo == "venda":
                        produto = st.selectbox("Produto:", ["bolao", "raspadinha", "loteria_federal"])
                        quantidade = st.number_input("Quantidade:", min_value=1, value=1)
                        
                        # Preços padrão
                        precos = {"bolao": 5.0, "raspadinha": 2.0, "loteria_federal": 10.0}
                        valor = quantidade * precos[produto]
                        st.write(f"**Valor Total: R$ {valor:.2f}**")
                    else:
                        produto = ""
                        quantidade = 0
                        valor = st.number_input("Valor (R$):", min_value=0.01, value=10.0, step=0.01)
                
                with col2:
                    observacoes = st.text_area("Observações:", height=100)
                
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
                    
                    st.success("✅ Lançamento salvo no Google Sheets!")
                    st.rerun()
        
        with tab2:
            st.markdown("#### Histórico de Lançamentos")
            
            # Carregar dados
            data = sheet.get_all_records()
            
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("📋 Nenhum lançamento registrado ainda.")
                
    except Exception as e:
        st.error(f"Erro ao processar lançamentos: {e}")

# ---------------------------
# Gestão do Cofre
# ---------------------------
def render_cofre(spreadsheet):
    st.subheader("🏦 Gestão do Cofre")
    
    try:
        # Obter worksheet do cofre
        cofre_sheet = get_or_create_worksheet(
            spreadsheet,
            "Cofre",
            ["Data", "Hora", "Tipo", "Valor", "Saldo", "Descrição"]
        )
        
        # Obter saldo atual
        cofre_data = cofre_sheet.get_all_records()
        saldo_atual = float(cofre_data[-1]["Saldo"]) if cofre_data else 1000.0
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.metric("💰 Saldo Atual", f"R$ {saldo_atual:.2f}")
            
            st.markdown("#### Nova Movimentação")
            
            with st.form("form_cofre"):
                tipo_mov = st.selectbox("Tipo:", ["entrada", "saida"])
                valor_mov = st.number_input("Valor (R$):", min_value=0.01, value=10.0)
                descricao = st.text_input("Descrição:")
                
                registrar = st.form_submit_button("💾 Registrar")
                
                if registrar:
                    if tipo_mov == "saida" and valor_mov > saldo_atual:
                        st.error("❌ Saldo insuficiente!")
                    else:
                        # Calcular novo saldo
                        if tipo_mov == "entrada":
                            novo_saldo = saldo_atual + valor_mov
                        else:
                            novo_saldo = saldo_atual - valor_mov
                        
                        # Salvar movimentação
                        nova_linha = [
                            str(date.today()),
                            datetime.now().strftime("%H:%M:%S"),
                            tipo_mov,
                            valor_mov,
                            novo_saldo,
                            descricao
                        ]
                        
                        cofre_sheet.append_row(nova_linha)
                        st.success("✅ Movimentação registrada no Google Sheets!")
                        st.rerun()
        
        with col2:
            st.markdown("#### Histórico de Movimentações")
            
            if cofre_data:
                df = pd.DataFrame(cofre_data)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("📋 Nenhuma movimentação registrada.")
                
    except Exception as e:
        st.error(f"Erro ao processar cofre: {e}")

# Função auxiliar para atualizar cofre
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
        st.error(f"Erro ao atualizar cofre: {e}")

# ---------------------------
# Outras funções (simplificadas)
# ---------------------------
def render_estoque(spreadsheet):
    st.subheader("📦 Gestão de Estoque")
    st.info("🚧 Funcionalidade de estoque será implementada na próxima versão.")

def render_relatorios(spreadsheet):
    st.subheader("📊 Relatórios")
    
    try:
        # Carregar dados dos lançamentos
        lancamentos_sheet = spreadsheet.worksheet("Lançamentos Caixa")
        data = lancamentos_sheet.get_all_records()
        
        if data:
            df = pd.DataFrame(data)
            
            # Filtrar apenas vendas
            vendas = df[df["Tipo"] == "venda"]
            
            if not vendas.empty:
                # Vendas por produto
                vendas_produto = vendas.groupby("Produto")["Valor"].sum().reset_index()
                fig = px.pie(vendas_produto, values="Valor", names="Produto", title="Vendas por Produto")
                st.plotly_chart(fig, use_container_width=True)
                
                # Tabela detalhada
                st.dataframe(vendas, use_container_width=True)
            else:
                st.info("📊 Nenhuma venda registrada.")
        else:
            st.info("📊 Nenhum dado disponível.")
            
    except Exception as e:
        st.error(f"Erro ao gerar relatórios: {e}")

def render_configuracoes():
    st.subheader("⚙️ Configurações")
    st.info("🚧 Configurações serão implementadas na próxima versão.")

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

