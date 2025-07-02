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

# Função para buscar dados com cache otimizado
@st.cache_data(ttl=60)
def buscar_dados(_spreadsheet, sheet_name):
    try:
        worksheet = _spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return data
    except Exception as e:
        st.warning(f"Planilha '{sheet_name}' não encontrada. Será criada automaticamente.")
        return []

# Função para criar ou obter worksheet
def get_or_create_worksheet(spreadsheet, sheet_name, headers):
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        return worksheet
    except:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="20")
        worksheet.append_row(headers)
        return worksheet

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
        if not all(campo in registro for campo in ['Valor_Bruto', 'Taxa_Cliente', 'Valor_Liquido']):
            dados_corrigidos.append(registro_corrigido)
            continue
            
        try:
            valor_bruto = float(registro['Valor_Bruto'])
            taxa_cliente = float(registro['Taxa_Cliente'])
            valor_liquido = float(registro['Valor_Liquido'])
            
            # Se valor bruto é 0, pular validação
            if valor_bruto == 0:
                dados_corrigidos.append(registro_corrigido)
                continue
            
            # Testar diferentes fatores de correção
            fatores_teste = [1, 0.01, 0.1, 10, 100]
            melhor_fator_taxa = 1
            melhor_fator_liquido = 1
            menor_erro = float('inf')
            
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
                registro_corrigido['Taxa_Cliente'] = taxa_cliente * melhor_fator_taxa
                
            if melhor_fator_liquido != 1:
                registro_corrigido['Valor_Liquido'] = valor_liquido * melhor_fator_liquido
            
            # Corrigir outros campos relacionados se existirem
            if 'Taxa_Banco' in registro and melhor_fator_taxa != 1:
                taxa_banco = float(registro.get('Taxa_Banco', 0))
                registro_corrigido['Taxa_Banco'] = taxa_banco * melhor_fator_taxa
                
            if 'Lucro' in registro and melhor_fator_taxa != 1:
                lucro = float(registro.get('Lucro', 0))
                registro_corrigido['Lucro'] = lucro * melhor_fator_taxa
                
        except (ValueError, TypeError):
            # Se houver erro na conversão, manter dados originais
            pass
            
        dados_corrigidos.append(registro_corrigido)
    
    return dados_corrigidos

# Função para limpar cache forçadamente
def limpar_cache_forcado():
    st.cache_data.clear()
    if 'simulacao_atual' in st.session_state:
        del st.session_state.simulacao_atual

# Função de debug para valores
def debug_valores(dados, titulo="Debug"):
    if st.checkbox(f"🔍 Debug - {titulo}"):
        st.write("**Dados brutos:**")
        for i, registro in enumerate(dados[:3]):  # Mostrar apenas 3 primeiros
            st.write(f"Registro {i+1}:")
            for campo in ['Valor_Bruto', 'Taxa_Cliente', 'Taxa_Banco', 'Valor_Liquido', 'Lucro']:
                if campo in registro:
                    st.write(f"  {campo}: {registro[campo]} (tipo: {type(registro[campo])})")

# Funções de cálculo corrigidas
def calcular_taxa_cartao_debito(valor):
    valor_dec = Decimal(str(valor))
    taxa_cliente = (valor_dec * Decimal('0.01')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)  # 1% sobre o valor
    taxa_banco = Decimal('1.00')   # Taxa fixa de R$ 1,00 que o banco cobra da empresa
    lucro = taxa_cliente - taxa_banco  # Lucro = taxa cliente - taxa banco
    valor_liquido = valor_dec - taxa_cliente
    
    return {
        "taxa_cliente": float(taxa_cliente),
        "taxa_banco": float(taxa_banco),
        "lucro": float(max(Decimal('0'), lucro)),  # Lucro não pode ser negativo
        "valor_liquido": float(valor_liquido)
    }

def calcular_taxa_cartao_credito(valor):
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

def calcular_taxa_cheque_vista(valor):
    valor_dec = Decimal(str(valor))
    taxa_cliente = (valor_dec * Decimal('0.02')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    taxa_banco = Decimal('0.00')
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
    taxa_base = valor_dec * Decimal('0.02')  # 2% base
    taxa_adicional = valor_dec * Decimal('0.0033') * Decimal(str(dias))  # 0.33% por dia
    taxa_cliente = (taxa_base + taxa_adicional).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    taxa_banco = Decimal('0.00')
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
    taxa_perc_dec = Decimal(str(taxa_percentual)) / Decimal('100')
    taxa_cliente = (valor_dec * taxa_perc_dec).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    taxa_banco = Decimal('0.00')
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
    if 'logado' not in st.session_state:
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
                        st.session_state.nome_usuario = tipo_usuario.split(" ")[1]
                        st.success(f"✅ Login realizado com sucesso! Bem-vindo, {st.session_state.nome_usuario}!")
                        st.rerun()
                    else:
                        st.error("❌ Senha incorreta!")
        return False
    return True

# Função principal do dashboard do caixa
def render_dashboard_caixa(spreadsheet):
    st.subheader("💳 Dashboard Caixa Interno")
    
    HEADERS = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]
    operacoes_data = buscar_dados(spreadsheet, "Operacoes_Caixa")
    
    if not operacoes_data:
        st.info("📊 Nenhuma operação registrada para exibir o dashboard.")
        return
    
    try:
        # Normalizar dados
        operacoes_data_normalizada = normalizar_dados_inteligente(operacoes_data)
        df_operacoes = pd.DataFrame(operacoes_data_normalizada)
        
        # Converter colunas numéricas
        for col in ['Valor_Bruto', 'Valor_Liquido', 'Taxa_Cliente', 'Taxa_Banco', 'Lucro']:
            if col in df_operacoes.columns:
                df_operacoes[col] = pd.to_numeric(df_operacoes[col], errors='coerce').fillna(0)
        
        # Calcular métricas
        total_suprimentos = df_operacoes[df_operacoes['Tipo_Operacao'] == 'Suprimento']['Valor_Bruto'].sum()
        tipos_de_saida = ["Saque Cartão Débito", "Saque Cartão Crédito", "Troca Cheque à Vista", "Troca Cheque Pré-datado", "Troca Cheque com Taxa Manual"]
        total_saques_liquidos = df_operacoes[df_operacoes['Tipo_Operacao'].isin(tipos_de_saida)]['Valor_Liquido'].sum()
        
        # Saldo do caixa (saldo inicial + suprimentos - saques líquidos)
        saldo_inicial = 5000.00  # Saldo inicial configurado
        saldo_caixa = saldo_inicial + total_suprimentos - total_saques_liquidos
        
        # Operações de hoje
        hoje_str = str(date.today())
        operacoes_de_hoje = df_operacoes[df_operacoes['Data'] == hoje_str]
        operacoes_hoje_count = len(operacoes_de_hoje)
        valor_saque_hoje = operacoes_de_hoje[operacoes_de_hoje['Tipo_Operacao'].isin(tipos_de_saida)]['Valor_Bruto'].sum()
        
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
                labels={
                    'Tipo_Operacao': 'Tipo de Operação', 
                    'Valor_Liquido': 'Valor Líquido Total (R$)'
                },
                color='Tipo_Operacao',
                text_auto='.2f'
            )
            fig.update_layout(
                showlegend=False,
                height=400,
                font=dict(family="Inter, sans-serif")
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 Nenhuma operação nos últimos 7 dias para exibir no gráfico.")
        
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
        
        # Estatísticas adicionais
        st.markdown("---")
        st.subheader("📈 Estatísticas Detalhadas")
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        
        with col_stat1:
            total_taxas_hoje = operacoes_de_hoje['Taxa_Cliente'].sum()
            st.metric("💰 Total Taxas Hoje", f"R$ {total_taxas_hoje:,.2f}")
        
        with col_stat2:
            total_lucro_hoje = operacoes_de_hoje['Lucro'].sum()
            st.metric("📈 Lucro Hoje", f"R$ {total_lucro_hoje:,.2f}")
        
        with col_stat3:
            if not df_recente.empty:
                media_operacao = df_recente['Valor_Bruto'].mean()
                st.metric("📊 Média por Operação", f"R$ {media_operacao:,.2f}")
            else:
                st.metric("📊 Média por Operação", "R$ 0,00")
        
    except Exception as e:
        st.error(f"Erro ao carregar dashboard: {e}")
        st.exception(e)

# Função melhorada para gestão do cofre com interface dinâmica
def render_cofre(spreadsheet):
    st.subheader("🏦 Gestão do Cofre")
    
    HEADERS_COFRE = ["Data", "Hora", "Operador", "Tipo_Transacao", "Valor", "Destino_Origem", "Observacoes"]
    cofre_data = buscar_dados(spreadsheet, "Operacoes_Cofre")
    df_cofre = pd.DataFrame(cofre_data)
    
    # Calcular saldo do cofre
    saldo_cofre = Decimal('0')
    if not df_cofre.empty and 'Tipo_Transacao' in df_cofre.columns and 'Valor' in df_cofre.columns:
        df_cofre['Valor'] = pd.to_numeric(df_cofre['Valor'], errors='coerce').fillna(0)
        df_cofre['Tipo_Transacao'] = df_cofre['Tipo_Transacao'].astype(str)
        entradas = df_cofre[df_cofre['Tipo_Transacao'] == 'Entrada no Cofre']['Valor'].sum()
        saidas = df_cofre[df_cofre['Tipo_Transacao'] == 'Saída do Cofre']['Valor'].sum()
        saldo_cofre = Decimal(str(entradas)) - Decimal(str(saidas))
    
    # Exibir saldo
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
        
        # Inicializar session_state para campos dinâmicos
        if 'cofre_tipo_mov' not in st.session_state:
            st.session_state.cofre_tipo_mov = "Entrada no Cofre"
        if 'cofre_valor' not in st.session_state:
            st.session_state.cofre_valor = 0.01
        if 'cofre_observacoes' not in st.session_state:
            st.session_state.cofre_observacoes = ""
        
        # Tipo de movimentação com callback
        tipo_mov = st.selectbox(
            "Tipo de Movimentação", 
            ["Entrada no Cofre", "Saída do Cofre"],
            key="cofre_tipo_mov_select",
            on_change=lambda: setattr(st.session_state, 'cofre_tipo_mov', st.session_state.cofre_tipo_mov_select)
        )
        
        # Atualizar session_state
        st.session_state.cofre_tipo_mov = tipo_mov
        
        # Valor da movimentação
        valor = st.number_input(
            "Valor da Movimentação (R$)", 
            min_value=0.01, 
            step=100.0,
            value=st.session_state.cofre_valor,
            key="cofre_valor_input"
        )
        st.session_state.cofre_valor = valor
        
        # Campos dinâmicos baseados no tipo de movimentação
        destino_final = ""
        
        if tipo_mov == "Saída do Cofre":
            st.markdown("##### 📤 Configurações de Saída")
            
            tipo_saida = st.selectbox(
                "Tipo de Saída:", 
                ["Transferência para Caixa", "Pagamento de Despesa"],
                key="cofre_tipo_saida"
            )
            
            if tipo_saida == "Transferência para Caixa":
                destino_caixa = st.selectbox(
                    "Transferir para:", 
                    ["Caixa Interno", "Caixa Lotérica"],
                    key="cofre_destino_caixa"
                )
                
                if destino_caixa == "Caixa Lotérica":
                    destino_pdv = st.selectbox(
                        "Selecione o PDV:", 
                        ["PDV 1", "PDV 2"],
                        key="cofre_destino_pdv"
                    )
                    destino_final = f"{destino_caixa} - {destino_pdv}"
                else:
                    destino_final = destino_caixa
            else:
                destino_final = st.text_input(
                    "Descrição da Despesa (Ex: Aluguel, Fornecedor X)",
                    key="cofre_descricao_despesa"
                )
        else:
            st.markdown("##### 📥 Configurações de Entrada")
            destino_final = st.text_input(
                "Origem da Entrada (Ex: Banco, Sócio)",
                key="cofre_origem_entrada"
            )
        
        # Observações
        observacoes = st.text_area(
            "Observações Adicionais",
            value=st.session_state.cofre_observacoes,
            key="cofre_observacoes_input"
        )
        st.session_state.cofre_observacoes = observacoes
        
        # Botões de ação
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🧮 Simular Operação", use_container_width=True, key="cofre_simular"):
                st.markdown("---")
                st.markdown("### 📊 Simulação da Operação")
                
                if tipo_mov == "Entrada no Cofre":
                    novo_saldo = saldo_cofre + Decimal(str(valor))
                    st.success(f"""
                    **💰 Entrada no Cofre:**
                    - Valor: R$ {valor:,.2f}
                    - Origem: {destino_final}
                    - Saldo Atual: R$ {saldo_cofre:,.2f}
                    - **Novo Saldo: R$ {novo_saldo:,.2f}**
                    """)
                else:
                    novo_saldo = saldo_cofre - Decimal(str(valor))
                    if novo_saldo < 0:
                        st.error(f"""
                        **❌ Saldo Insuficiente:**
                        - Valor da Saída: R$ {valor:,.2f}
                        - Saldo Atual: R$ {saldo_cofre:,.2f}
                        - **Saldo seria: R$ {novo_saldo:,.2f}** (NEGATIVO!)
                        """)
                    else:
                        st.success(f"""
                        **📤 Saída do Cofre:**
                        - Valor: R$ {valor:,.2f}
                        - Destino: {destino_final}
                        - Saldo Atual: R$ {saldo_cofre:,.2f}
                        - **Novo Saldo: R$ {novo_saldo:,.2f}**
                        """)
        
        with col_btn2:
            if st.button("💾 Confirmar e Salvar", use_container_width=True, key="cofre_salvar"):
                # Validações
                if not destino_final.strip():
                    st.error("❌ Por favor, preencha o campo de origem/destino!")
                    st.stop()
                
                if tipo_mov == "Saída do Cofre" and valor > float(saldo_cofre):
                    st.error("❌ Saldo insuficiente no cofre!")
                    st.stop()
                
                # Salvar no Google Sheets
                cofre_sheet = get_or_create_worksheet(spreadsheet, "Operacoes_Cofre", HEADERS_COFRE)
                nova_mov_cofre = [
                    str(date.today()), 
                    datetime.now().strftime("%H:%M:%S"), 
                    st.session_state.nome_usuario, 
                    tipo_mov, 
                    float(valor), 
                    destino_final, 
                    observacoes
                ]
                cofre_sheet.append_row(nova_mov_cofre)
                
                # Se for transferência para Caixa Interno, criar suprimento
                if tipo_mov == "Saída do Cofre" and destino_final == "Caixa Interno":
                    HEADERS_CAIXA = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]
                    caixa_sheet = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", HEADERS_CAIXA)
                    nova_operacao_caixa = [
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
                        f"Transferência do Cofre para: {destino_final}"
                    ]
                    caixa_sheet.append_row(nova_operacao_caixa)
                    st.success(f"✅ Saída de R$ {valor:,.2f} do cofre registrada e suprimento criado no Caixa Interno!")
                
                elif tipo_mov == "Saída do Cofre" and "Caixa Lotérica" in destino_final:
                    st.info(f"Saída para {destino_final} registrada. A integração de suprimento com o caixa da lotérica será implementada futuramente.")
                    st.success(f"✅ Movimentação de R$ {valor:,.2f} no cofre registrada com sucesso!")
                
                else:
                    st.success(f"✅ Movimentação de R$ {valor:,.2f} no cofre registrada com sucesso!")
                
                # Limpar cache e resetar campos
                st.cache_data.clear()
                
                # Resetar session_state
                st.session_state.cofre_valor = 0.01
                st.session_state.cofre_observacoes = ""
                
                # Rerun para atualizar interface
                st.rerun()
    
    with tab2:
        st.markdown("#### Histórico de Movimentações")
        if not df_cofre.empty:
            if 'Data' in df_cofre.columns and 'Hora' in df_cofre.columns:
                df_cofre_sorted = df_cofre.sort_values(by=['Data', 'Hora'], ascending=False)
                
                # Formatação monetária
                if 'Valor' in df_cofre_sorted.columns:
                    df_cofre_display = df_cofre_sorted.copy()
                    df_cofre_display['Valor'] = df_cofre_display['Valor'].apply(
                        lambda x: f"R$ {float(x):,.2f}" if pd.notnull(x) else "R$ 0,00"
                    )
                    st.dataframe(df_cofre_display, use_container_width=True)
                else:
                    st.dataframe(df_cofre_sorted, use_container_width=True)
            else:
                st.dataframe(df_cofre, use_container_width=True)
        else:
            st.info("Nenhuma movimentação registrada no cofre.")

# Função para operações do caixa
def render_operacoes_caixa(spreadsheet):
    st.subheader("💳 Operações do Caixa Interno")
    
    HEADERS_CAIXA = ["Data", "Hora", "Operador", "Tipo_Operacao", "Cliente", "CPF", "Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Status", "Data_Vencimento_Cheque", "Taxa_Percentual", "Observacoes"]
    
    # Tabs para diferentes operações
    tab1, tab2, tab3, tab4 = st.tabs([
        "💳 Saque Cartão", 
        "📄 Troca de Cheques", 
        "💰 Suprimento Caixa",
        "📊 Histórico"
    ])
    
    with tab1:
        render_saque_cartao(spreadsheet, HEADERS_CAIXA)
    
    with tab2:
        render_troca_cheques(spreadsheet, HEADERS_CAIXA)
    
    with tab3:
        render_suprimento_caixa(spreadsheet, HEADERS_CAIXA)
    
    with tab4:
        render_historico_operacoes(spreadsheet)

def render_saque_cartao(spreadsheet, headers):
    st.markdown("#### 💳 Saque Cartão (Débito/Crédito)")
    
    with st.form("form_saque_cartao", clear_on_submit=False):
        col1, col2 = st.columns(2)
        
        with col1:
            nome = st.text_input("Nome do Cliente", placeholder="Opcional")
            valor = st.number_input("Valor do Saque (R$)", min_value=0.01, step=50.0)
        
        with col2:
            cpf = st.text_input("CPF do Cliente", placeholder="Opcional")
            tipo_cartao = st.selectbox("Tipo de Cartão", ["Débito", "Crédito"])
        
        observacoes = st.text_area("Observações", placeholder="Informações adicionais...")
        
        # Botão de simulação
        col_sim, col_conf = st.columns(2)
        
        with col_sim:
            simular = st.form_submit_button("🧮 Simular Operação", use_container_width=True)
        
        if simular:
            if tipo_cartao == "Débito":
                calc = calcular_taxa_cartao_debito(valor)
            else:
                calc = calcular_taxa_cartao_credito(valor)
            
            st.markdown("---")
            st.markdown(f"### ✅ Simulação - Cartão {tipo_cartao}")
            
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                st.metric("Taxa Percentual", f"{(calc['taxa_cliente']/valor)*100:.2f}%")
                st.metric("Taxa em Valores", f"R$ {calc['taxa_cliente']:,.2f}")
            
            with col_res2:
                st.metric("💵 Valor a Entregar", f"R$ {calc['valor_liquido']:,.2f}")
                if tipo_cartao == "Débito":
                    st.info("💡 Taxa de 1% sobre o valor do saque")
                else:
                    st.info("💡 Taxa de 5,33% sobre o valor do saque")
            
            st.session_state.simulacao_atual = {
                'tipo': f'Saque Cartão {tipo_cartao}',
                'dados': calc,
                'valor_bruto': valor,
                'nome': nome or "Não informado",
                'cpf': cpf or "Não informado",
                'observacoes': observacoes
            }
        
        with col_conf:
            confirmar = st.form_submit_button("💾 Confirmar e Salvar", use_container_width=True)
        
        if confirmar:
            if 'simulacao_atual' not in st.session_state:
                st.error("❌ Faça a simulação primeiro!")
                st.stop()
            
            sim = st.session_state.simulacao_atual
            if tipo_cartao == "Débito":
                calc = calcular_taxa_cartao_debito(valor)
            else:
                calc = calcular_taxa_cartao_credito(valor)
            
            # Salvar operação
            caixa_sheet = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", headers)
            nova_operacao = [
                str(date.today()),
                datetime.now().strftime("%H:%M:%S"),
                st.session_state.nome_usuario,
                f"Saque Cartão {tipo_cartao}",
                nome or "Não informado",
                cpf or "Não informado",
                float(valor),
                calc['taxa_cliente'],
                calc['taxa_banco'],
                calc['valor_liquido'],
                calc['lucro'],
                "Concluído",
                "",
                f"{(calc['taxa_cliente']/valor)*100:.2f}%",
                observacoes
            ]
            caixa_sheet.append_row(nova_operacao)
            
            st.success(f"✅ Saque de R$ {valor:,.2f} registrado! Entregar R$ {calc['valor_liquido']:,.2f} ao cliente.")
            
            # Limpar simulação
            if 'simulacao_atual' in st.session_state:
                del st.session_state.simulacao_atual
            
            st.cache_data.clear()

def render_troca_cheques(spreadsheet, headers):
    st.markdown("#### 📄 Troca de Cheques")
    
    tipo_cheque = st.selectbox("Tipo de Cheque", [
        "Cheque à Vista", 
        "Cheque Pré-datado", 
        "Cheque com Taxa Manual"
    ])
    
    with st.form("form_troca_cheque", clear_on_submit=False):
        col1, col2 = st.columns(2)
        
        with col1:
            nome = st.text_input("Nome do Cliente", placeholder="Opcional")
            valor = st.number_input("Valor do Cheque (R$)", min_value=0.01, step=100.0)
        
        with col2:
            cpf = st.text_input("CPF do Cliente", placeholder="Opcional")
            
            if tipo_cheque == "Cheque Pré-datado":
                data_vencimento = st.date_input("Data de Vencimento", min_value=date.today())
                dias = (data_vencimento - date.today()).days
                st.info(f"📅 Dias até vencimento: {dias}")
            elif tipo_cheque == "Cheque com Taxa Manual":
                taxa_manual = st.number_input("Taxa Percentual (%)", min_value=0.1, max_value=50.0, step=0.1)
        
        observacoes = st.text_area("Observações", placeholder="Banco, Cheque nº, etc...")
        
        # Botões
        col_sim, col_conf = st.columns(2)
        
        with col_sim:
            simular = st.form_submit_button("🧮 Simular Operação", use_container_width=True)
        
        if simular:
            if tipo_cheque == "Cheque à Vista":
                calc = calcular_taxa_cheque_vista(valor)
                data_venc = str(date.today())
            elif tipo_cheque == "Cheque Pré-datado":
                calc = calcular_taxa_cheque_pre_datado(valor, dias)
                data_venc = str(data_vencimento)
            else:
                calc = calcular_taxa_cheque_manual(valor, taxa_manual)
                data_venc = str(date.today())
            
            st.markdown("---")
            st.markdown(f"### ✅ Simulação - {tipo_cheque}")
            
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                st.metric("Taxa Percentual", f"{(calc['taxa_cliente']/valor)*100:.2f}%")
                st.metric("Taxa em Valores", f"R$ {calc['taxa_cliente']:,.2f}")
            
            with col_res2:
                st.metric("💵 Valor a Entregar", f"R$ {calc['valor_liquido']:,.2f}")
                if tipo_cheque == "Cheque à Vista":
                    st.info("💡 Taxa de 2% sobre o valor do cheque")
                elif tipo_cheque == "Cheque Pré-datado":
                    st.info(f"💡 Taxa de 2% + 0,33% por dia ({dias} dias)")
                else:
                    st.info(f"💡 Taxa manual de {taxa_manual}%")
            
            st.session_state.simulacao_atual = {
                'tipo': tipo_cheque,
                'dados': calc,
                'valor_bruto': valor,
                'nome': nome or "Não informado",
                'cpf': cpf or "Não informado",
                'observacoes': observacoes,
                'data_vencimento': data_venc
            }
        
        with col_conf:
            confirmar = st.form_submit_button("💾 Confirmar e Salvar", use_container_width=True)
        
        if confirmar:
            if 'simulacao_atual' not in st.session_state:
                st.error("❌ Faça a simulação primeiro!")
                st.stop()
            
            sim = st.session_state.simulacao_atual
            
            # Recalcular para garantir consistência
            if tipo_cheque == "Cheque à Vista":
                calc = calcular_taxa_cheque_vista(valor)
                data_venc = str(date.today())
            elif tipo_cheque == "Cheque Pré-datado":
                calc = calcular_taxa_cheque_pre_datado(valor, dias)
                data_venc = str(data_vencimento)
            else:
                calc = calcular_taxa_cheque_manual(valor, taxa_manual)
                data_venc = str(date.today())
            
            # Salvar operação
            caixa_sheet = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", headers)
            nova_operacao = [
                str(date.today()),
                datetime.now().strftime("%H:%M:%S"),
                st.session_state.nome_usuario,
                f"Troca {tipo_cheque}",
                nome or "Não informado",
                cpf or "Não informado",
                float(valor),
                calc['taxa_cliente'],
                calc['taxa_banco'],
                calc['valor_liquido'],
                calc['lucro'],
                "Concluído",
                data_venc,
                f"{(calc['taxa_cliente']/valor)*100:.2f}%",
                f"Banco: ; Cheque: ; {observacoes}"
            ]
            caixa_sheet.append_row(nova_operacao)
            
            st.success(f"✅ {tipo_cheque} de R$ {valor:,.2f} registrado! Entregar R$ {calc['valor_liquido']:,.2f} ao cliente.")
            
            # Limpar simulação
            if 'simulacao_atual' in st.session_state:
                del st.session_state.simulacao_atual
            
            st.cache_data.clear()

def render_suprimento_caixa(spreadsheet, headers):
    st.markdown("#### 💰 Suprimento do Caixa")
    
    if st.session_state.tipo_usuario != "👑 Gerente":
        st.warning("⚠️ Apenas o gerente pode fazer suprimentos do cofre.")
        return
    
    with st.form("form_suprimento", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            valor = st.number_input("Valor do Suprimento (R$)", min_value=0.01, step=100.0)
            origem = st.selectbox("Origem do Suprimento", [
                "Cofre Principal", 
                "Depósito Bancário", 
                "Outro"
            ])
        
        with col2:
            if origem == "Outro":
                origem_desc = st.text_input("Especificar Origem")
            else:
                origem_desc = origem
            
            observacoes = st.text_area("Observações")
        
        submitted = st.form_submit_button("💾 Registrar Suprimento", use_container_width=True)
        
        if submitted:
            caixa_sheet = get_or_create_worksheet(spreadsheet, "Operacoes_Caixa", headers)
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
                f"Origem: {origem_desc}. {observacoes}"
            ]
            caixa_sheet.append_row(nova_operacao)
            
            st.success(f"✅ Suprimento de R$ {valor:,.2f} registrado com sucesso!")
            st.cache_data.clear()

def render_historico_operacoes(spreadsheet):
    st.markdown("#### 📊 Histórico de Operações")
    
    # Buscar dados
    caixa_data = buscar_dados(spreadsheet, "Operacoes_Caixa")
    
    if not caixa_data:
        st.info("📊 Nenhuma operação registrada ainda.")
        return
    
    # Normalizar dados
    caixa_data_normalizada = normalizar_dados_inteligente(caixa_data)
    df_caixa = pd.DataFrame(caixa_data_normalizada)
    
    if df_caixa.empty:
        st.info("📊 Nenhuma operação encontrada.")
        return
    
    # Filtros
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        if 'Data' in df_caixa.columns:
            data_inicio = st.date_input("Data Início", value=date.today() - timedelta(days=7))
        else:
            data_inicio = date.today() - timedelta(days=7)
    
    with col_f2:
        if 'Data' in df_caixa.columns:
            data_fim = st.date_input("Data Fim", value=date.today())
        else:
            data_fim = date.today()
    
    with col_f3:
        if 'Tipo_Operacao' in df_caixa.columns:
            tipos_disponiveis = df_caixa['Tipo_Operacao'].unique().tolist()
            tipo_filtro = st.selectbox("Tipo de Operação", ["Todos"] + tipos_disponiveis)
        else:
            tipo_filtro = "Todos"
    
    # Aplicar filtros
    df_filtrado = df_caixa.copy()
    
    if 'Data' in df_filtrado.columns:
        df_filtrado['Data'] = pd.to_datetime(df_filtrado['Data'], errors='coerce').dt.date
        df_filtrado = df_filtrado[
            (df_filtrado['Data'] >= data_inicio) & 
            (df_filtrado['Data'] <= data_fim)
        ]
    
    if tipo_filtro != "Todos" and 'Tipo_Operacao' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['Tipo_Operacao'] == tipo_filtro]
    
    # Exibir dados
    if not df_filtrado.empty:
        # Ordenar por data e hora
        if 'Data' in df_filtrado.columns and 'Hora' in df_filtrado.columns:
            df_filtrado = df_filtrado.sort_values(by=['Data', 'Hora'], ascending=False)
        
        # Formatação monetária para exibição
        df_exibicao = df_filtrado.copy()
        colunas_numericas = ['Valor_Bruto', 'Taxa_Cliente', 'Taxa_Banco', 'Valor_Liquido', 'Lucro']
        
        for col in colunas_numericas:
            if col in df_exibicao.columns:
                df_exibicao[col] = df_exibicao[col].apply(
                    lambda x: f"R$ {float(x):,.2f}" if pd.notnull(x) and x != 0 else "R$ 0,00"
                )
        
        st.dataframe(df_exibicao, use_container_width=True)
        
        # Estatísticas
        st.markdown("---")
        st.markdown("### 📈 Estatísticas do Período")
        
        col_e1, col_e2, col_e3, col_e4 = st.columns(4)
        
        with col_e1:
            total_operacoes = len(df_filtrado)
            st.metric("Total de Operações", total_operacoes)
        
        with col_e2:
            if 'Valor_Bruto' in df_filtrado.columns:
                total_movimentado = df_filtrado['Valor_Bruto'].sum()
                st.metric("Total Movimentado", f"R$ {total_movimentado:,.2f}")
        
        with col_e3:
            if 'Taxa_Cliente' in df_filtrado.columns:
                total_taxas = df_filtrado['Taxa_Cliente'].sum()
                st.metric("Total em Taxas", f"R$ {total_taxas:,.2f}")
        
        with col_e4:
            if 'Lucro' in df_filtrado.columns:
                total_lucro = df_filtrado['Lucro'].sum()
                st.metric("Lucro Total", f"R$ {total_lucro:,.2f}")
    
    else:
        st.info("📊 Nenhuma operação encontrada para os filtros selecionados.")

# Função para fechamento da lotérica
def render_fechamento_loterica(spreadsheet):
    st.subheader("📋 Fechamento de Caixa Lotérica")
    
    HEADERS_FECHAMENTO = ["Data_Fechamento", "PDV", "Operador", "Qtd_Compra_Bolao", "Custo_Unit_Bolao", "Total_Compra_Bolao", "Qtd_Compra_Raspadinha", "Custo_Unit_Raspadinha", "Total_Compra_Raspadinha", "Qtd_Compra_LoteriaFederal", "Custo_Unit_LoteriaFederal", "Total_Compra_LoteriaFederal", "Qtd_Venda_Bolao", "Preco_Unit_Bolao", "Total_Venda_Bolao", "Qtd_Venda_Raspadinha", "Preco_Unit_Raspadinha", "Total_Venda_Raspadinha", "Qtd_Venda_LoteriaFederal", "Preco_Unit_LoteriaFederal", "Total_Venda_LoteriaFederal", "Movimentacao_Cielo", "Pagamento_Premios", "Vales_Despesas", "Retirada_Cofre", "Retirada_CaixaInterno", "Dinheiro_Gaveta_Final", "Saldo_Anterior", "Saldo_Final_Calculado", "Diferenca_Caixa"]
    
    with st.form("form_fechamento_pdv", clear_on_submit=False):
        st.markdown("#### Lançar Fechamento Diário do PDV")
        
        col1, col2 = st.columns(2)
        with col1:
            pdv_selecionado = st.selectbox("Selecione o PDV", ["PDV 1", "PDV 2"])
        with col2:
            data_fechamento = st.date_input("Data do Fechamento", date.today())
        
        # Buscar saldo anterior
        sheet_name = f"Fechamentos_{pdv_selecionado.replace(' ', '')}"
        fechamentos_data = buscar_dados(spreadsheet, sheet_name)
        df_fechamentos = pd.DataFrame(fechamentos_data)
        
        saldo_anterior = Decimal('0')
        if not df_fechamentos.empty:
            df_fechamentos['Data_Fechamento'] = pd.to_datetime(df_fechamentos['Data_Fechamento'], errors='coerce').dt.date
            df_fechamentos['Saldo_Final_Calculado'] = pd.to_numeric(df_fechamentos['Saldo_Final_Calculado'], errors='coerce').fillna(0)
            
            data_anterior = data_fechamento - timedelta(days=1)
            registro_anterior = df_fechamentos[df_fechamentos['Data_Fechamento'] == data_anterior]
            if not registro_anterior.empty:
                saldo_anterior = Decimal(str(registro_anterior.iloc[0]['Saldo_Final_Calculado']))
        
        st.metric("Saldo Anterior (Fechamento de Ontem)", f"R$ {saldo_anterior:,.2f}")
        st.markdown("---")
        
        # Seções de lançamentos
        with st.expander("Lançamentos de Compras de Produtos (Custo)"):
            c1, c2, c3 = st.columns(3)
            
            with c1:
                st.write("**Bolão**")
                qtd_compra_bolao = st.number_input("Qtd Compra", min_value=0, key="qtd_c_bolao")
                custo_bolao = st.number_input("Custo Unit. (R$)", min_value=0.0, format="%.2f", key="custo_bolao")
                total_compra_bolao = qtd_compra_bolao * custo_bolao
            
            with c2:
                st.write("**Raspadinha**")
                qtd_compra_raspa = st.number_input("Qtd Compra", min_value=0, key="qtd_c_raspa")
                custo_raspa = st.number_input("Custo Unit. (R$)", min_value=0.0, format="%.2f", key="custo_raspa")
                total_compra_raspa = qtd_compra_raspa * custo_raspa
            
            with c3:
                st.write("**Loteria Federal**")
                qtd_compra_federal = st.number_input("Qtd Compra", min_value=0, key="qtd_c_federal")
                custo_federal = st.number_input("Custo Unit. (R$)", min_value=0.0, format="%.2f", key="custo_federal")
                total_compra_federal = qtd_compra_federal * custo_federal
        
        with st.expander("Lançamentos de Vendas de Produtos (Receita)"):
            v1, v2, v3 = st.columns(3)
            
            with v1:
                st.write("**Bolão**")
                qtd_venda_bolao = st.number_input("Qtd Venda", min_value=0, key="qtd_v_bolao")
                preco_bolao = st.number_input("Preço Unit. (R$)", min_value=0.0, format="%.2f", key="preco_bolao")
                total_venda_bolao = qtd_venda_bolao * preco_bolao
            
            with v2:
                st.write("**Raspadinha**")
                qtd_venda_raspa = st.number_input("Qtd Venda", min_value=0, key="qtd_v_raspa")
                preco_raspa = st.number_input("Preço Unit. (R$)", min_value=0.0, format="%.2f", key="preco_raspa")
                total_venda_raspa = qtd_venda_raspa * preco_raspa
            
            with v3:
                st.write("**Loteria Federal**")
                qtd_venda_federal = st.number_input("Qtd Venda", min_value=0, key="qtd_v_federal")
                preco_federal = st.number_input("Preço Unit. (R$)", min_value=0.0, format="%.2f", key="preco_federal")
                total_venda_federal = qtd_venda_federal * preco_federal
        
        with st.expander("Movimentações Financeiras"):
            f1, f2 = st.columns(2)
            
            with f1:
                movimentacao_cielo = st.number_input("Movimentação Cielo (R$)", format="%.2f")
                pagamento_premios = st.number_input("Pagamento de Prêmios (R$)", format="%.2f")
                vales_despesas = st.number_input("Vales e Despesas (R$)", format="%.2f")
            
            with f2:
                retirada_cofre = st.number_input("Retirada para Cofre (R$)", format="%.2f")
                retirada_caixa_interno = st.number_input("Retirada para Caixa Interno (R$)", format="%.2f")
                dinheiro_gaveta_final = st.number_input("Dinheiro na Gaveta Final (R$)", format="%.2f")
        
        # Cálculo automático do saldo
        total_compras = total_compra_bolao + total_compra_raspa + total_compra_federal
        total_vendas = total_venda_bolao + total_venda_raspa + total_venda_federal
        
        saldo_calculado = (float(saldo_anterior) + total_vendas + movimentacao_cielo - 
                          total_compras - pagamento_premios - vales_despesas - 
                          retirada_cofre - retirada_caixa_interno)
        
        diferenca_caixa = dinheiro_gaveta_final - saldo_calculado
        
        # Exibir resumo
        st.markdown("---")
        st.markdown("### 📊 Resumo do Fechamento")
        
        col_r1, col_r2, col_r3 = st.columns(3)
        
        with col_r1:
            st.metric("Total Compras", f"R$ {total_compras:,.2f}")
            st.metric("Total Vendas", f"R$ {total_vendas:,.2f}")
        
        with col_r2:
            st.metric("Saldo Calculado", f"R$ {saldo_calculado:,.2f}")
            st.metric("Dinheiro na Gaveta", f"R$ {dinheiro_gaveta_final:,.2f}")
        
        with col_r3:
            diferenca_cor = "🟢" if abs(diferenca_caixa) <= 5 else "🔴"
            st.metric("Diferença de Caixa", f"{diferenca_cor} R$ {diferenca_caixa:,.2f}")
        
        # Botão de salvar
        submitted = st.form_submit_button("💾 Salvar Fechamento", use_container_width=True)
        
        if submitted:
            fechamento_sheet = get_or_create_worksheet(spreadsheet, sheet_name, HEADERS_FECHAMENTO)
            
            novo_fechamento = [
                str(data_fechamento), pdv_selecionado, st.session_state.nome_usuario,
                qtd_compra_bolao, custo_bolao, total_compra_bolao,
                qtd_compra_raspa, custo_raspa, total_compra_raspa,
                qtd_compra_federal, custo_federal, total_compra_federal,
                qtd_venda_bolao, preco_bolao, total_venda_bolao,
                qtd_venda_raspa, preco_raspa, total_venda_raspa,
                qtd_venda_federal, preco_federal, total_venda_federal,
                movimentacao_cielo, pagamento_premios, vales_despesas,
                retirada_cofre, retirada_caixa_interno, dinheiro_gaveta_final,
                float(saldo_anterior), saldo_calculado, diferenca_caixa
            ]
            
            fechamento_sheet.append_row(novo_fechamento)
            
            if abs(diferenca_caixa) <= 5:
                st.success(f"✅ Fechamento do {pdv_selecionado} salvo com sucesso! Caixa conferido.")
            else:
                st.warning(f"⚠️ Fechamento salvo, mas há diferença de R$ {diferenca_caixa:,.2f} no caixa.")
            
            st.cache_data.clear()

# Menu principal
def main():
    if not verificar_login():
        return
    
    # Conectar ao Google Sheets
    spreadsheet = conectar_google_sheets()
    if not spreadsheet:
        st.error("❌ Não foi possível conectar ao Google Sheets. Verifique as credenciais.")
        return
    
    # Sidebar com navegação
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 1rem;">
            <h3 style="color: white; margin: 0;">👋 Olá, {st.session_state.nome_usuario}!</h3>
            <p style="color: white; margin: 0; opacity: 0.9;">{st.session_state.tipo_usuario}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🧭 Navegação")
        
        # Menu baseado no tipo de usuário
        if st.session_state.tipo_usuario == "👑 Gerente":
            # Dashboards
            st.markdown("#### 📊 Dashboards")
            if st.button("💳 Dashboard Caixa", use_container_width=True):
                st.session_state.pagina_atual = "dashboard_caixa"
            if st.button("🏦 Dashboard Cofre", use_container_width=True):
                st.session_state.pagina_atual = "cofre"
            
            # Operações
            st.markdown("#### ⚙️ Operações")
            if st.button("💳 Operações Caixa", use_container_width=True):
                st.session_state.pagina_atual = "operacoes_caixa"
            if st.button("🏦 Gestão do Cofre", use_container_width=True):
                st.session_state.pagina_atual = "cofre"
            if st.button("📋 Fechamento Lotérica", use_container_width=True):
                st.session_state.pagina_atual = "fechamento_loterica"
            
        elif st.session_state.tipo_usuario == "💳 Operador Caixa":
            # Dashboards
            st.markdown("#### 📊 Dashboards")
            if st.button("💳 Dashboard Caixa", use_container_width=True):
                st.session_state.pagina_atual = "dashboard_caixa"
            
            # Operações
            st.markdown("#### ⚙️ Operações")
            if st.button("💳 Operações Caixa", use_container_width=True):
                st.session_state.pagina_atual = "operacoes_caixa"
            
        elif st.session_state.tipo_usuario == "🎰 Operador Lotérica":
            # Operações
            st.markdown("#### ⚙️ Operações")
            if st.button("📋 Fechamento Lotérica", use_container_width=True):
                st.session_state.pagina_atual = "fechamento_loterica"
        
        st.markdown("---")
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.logado = False
            st.rerun()
    
    # Página inicial padrão
    if 'pagina_atual' not in st.session_state:
        if st.session_state.tipo_usuario == "👑 Gerente":
            st.session_state.pagina_atual = "dashboard_caixa"
        elif st.session_state.tipo_usuario == "💳 Operador Caixa":
            st.session_state.pagina_atual = "dashboard_caixa"
        else:
            st.session_state.pagina_atual = "fechamento_loterica"
    
    # Renderizar página atual
    if st.session_state.pagina_atual == "dashboard_caixa":
        render_dashboard_caixa(spreadsheet)
    elif st.session_state.pagina_atual == "operacoes_caixa":
        render_operacoes_caixa(spreadsheet)
    elif st.session_state.pagina_atual == "cofre":
        render_cofre(spreadsheet)
    elif st.session_state.pagina_atual == "fechamento_loterica":
        render_fechamento_loterica(spreadsheet)

if __name__ == "__main__":
    main()

