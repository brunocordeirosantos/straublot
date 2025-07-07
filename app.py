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

# ===== FUNÇÕES AUXILIARES PARA CONVERSÃO SEGURA =====

def to_decimal(value):
    """Converte qualquer valor para Decimal de forma segura"""
    try:
        if isinstance(value, Decimal):
            return value
        if isinstance(value, str):
            # Remove espaços e converte vírgulas para pontos se necessário
            value = value.strip().replace(',', '.')
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0')

def to_float(value):
    """Converte Decimal ou string para float de forma segura"""
    try:
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, str):
            value = value.strip().replace(',', '.')
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def format_currency_br(value):
    """Formata valor como moeda brasileira"""
    try:
        val = to_float(value)
        return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return "R$ 0,00"

def format_currency_us(value):
    """Formata valor no padrão americano para Google Sheets"""
    try:
        val = to_float(value)
        return f"{val:.2f}"
    except:
        return "0.00"

def safe_percentage(numerator, denominator):
    """Calcula porcentagem de forma segura"""
    try:
        num = to_float(numerator)
        den = to_float(denominator)
        if den == 0:
            return "0.00%"
        return f"{(num / den) * 100:.2f}%"
    except:
        return "0.00%"

#  Importar pytz com tratamento de erro
try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False

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
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* Cards de métricas */
    .metric-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        margin: 1rem 0;
    }
    
    /* Sidebar personalizada */
    .css-1d391kg {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Títulos */
    h1, h2, h3 {
        color: #2c3e50;
        font-weight: 600;
    }
    
    /* Alertas customizados */
    .stAlert {
        border-radius: 10px;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

# Configuração do Google Sheets
@st.cache_resource
def conectar_google_sheets():
    try:
        # Tentar usar Streamlit Secrets primeiro (para deploy)
        if hasattr(st, 'secrets') and 'google_sheets' in st.secrets:
            credentials_dict = dict(st.secrets["google_sheets"])
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                credentials_dict,
                ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            )
            client = gspread.authorize(credentials)
            spreadsheet = client.open("Caixa_Interno")
            return spreadsheet
        else:
            st.warning("⚠️ Credenciais do Google Sheets não configuradas. Sistema funcionando em modo demo.")
            return None
    except Exception as e:
        st.error(f"❌ Erro ao conectar com Google Sheets: {str(e)}")
        return None

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

def get_or_create_worksheet(spreadsheet, sheet_name, headers):
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="20")
        worksheet.append_row(headers)
    return worksheet

def normalizar_dados_inteligente(dados):
    """
    Normaliza dados vindos do Google Sheets, detectando e corrigindo automaticamente
    problemas de formatação numérica
    """
    if not dados:
        return dados
    
    dados_normalizados = []
    
    for registro in dados:
        registro_normalizado = {}
        
        for campo, valor in registro.items():
            if campo in ["Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro"]:
                try:
                    # Converter para Decimal de forma segura
                    if isinstance(valor, str):
                        # Remove espaços e trata vírgulas/pontos
                        valor_limpo = valor.strip().replace(',', '.')
                        valor_decimal = to_decimal(valor_limpo)
                    else:
                        valor_decimal = to_decimal(valor)
                    
                    registro_normalizado[campo] = valor_decimal
                except:
                    registro_normalizado[campo] = Decimal('0')
            else:
                registro_normalizado[campo] = valor
        
        dados_normalizados.append(registro_normalizado)
    
    return dados_normalizados

# Funções de cálculo corrigidas
def calcular_taxa_cartao_debito(valor):
    valor_dec = to_decimal(valor)
    taxa_cliente = (valor_dec * Decimal("0.01")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    taxa_banco = Decimal("1.00")
    lucro = max(Decimal("0.00"), taxa_cliente - taxa_banco)
    valor_liquido = valor_dec - taxa_cliente

    return {
        "taxa_cliente": taxa_cliente,
        "taxa_banco": taxa_banco,
        "lucro": lucro,
        "valor_liquido": valor_liquido
    }

def calcular_taxa_cartao_credito(valor):
    valor_dec = to_decimal(valor)
    taxa_cliente = (valor_dec * Decimal("0.0533")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    taxa_banco = (valor_dec * Decimal("0.0433")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    lucro = taxa_cliente - taxa_banco
    valor_liquido = valor_dec - taxa_cliente

    return {
        "taxa_cliente": taxa_cliente,
        "taxa_banco": taxa_banco,
        "lucro": max(Decimal("0"), lucro),
        "valor_liquido": valor_liquido
    }

def calcular_taxa_cheque_vista(valor):
    valor_dec = to_decimal(valor)
    taxa_cliente = (valor_dec * Decimal("0.02")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    taxa_banco = Decimal("0.00")
    lucro = taxa_cliente
    valor_liquido = valor_dec - taxa_cliente

    return {
        "taxa_cliente": taxa_cliente,
        "taxa_banco": taxa_banco,
        "lucro": max(Decimal("0"), lucro),
        "valor_liquido": valor_liquido
    }

def calcular_taxa_cheque_pre_datado(valor, dias):
    valor_dec = to_decimal(valor)
    taxa_percentual = Decimal("0.02") + Decimal("0.0033") * Decimal(dias)
    taxa_cliente = (valor_dec * taxa_percentual).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    taxa_banco = Decimal("0.00")
    lucro = taxa_cliente
    valor_liquido = valor_dec - taxa_cliente

    return {
        "taxa_cliente": taxa_cliente,
        "taxa_banco": taxa_banco,
        "lucro": max(Decimal("0"), lucro),
        "valor_liquido": valor_liquido
    }

def calcular_taxa_cheque_manual(valor, taxa_percentual):
    valor_dec = to_decimal(valor)
    taxa_decimal = to_decimal(taxa_percentual) / Decimal("100")
    taxa_cliente = (valor_dec * taxa_decimal).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    taxa_banco = Decimal("0.00")
    lucro = taxa_cliente
    valor_liquido = valor_dec - taxa_cliente

    return {
        "taxa_cliente": taxa_cliente,
        "taxa_banco": taxa_banco,
        "lucro": max(Decimal("0"), lucro),
        "valor_liquido": valor_liquido
    }

# Sistema de autenticação
def verificar_login():
    if "logado" not in st.session_state:
        st.session_state.logado = False
    
    if not st.session_state.logado:
        st.title("🔐 Login - Sistema Unificado")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 2rem; border-radius: 15px; text-align: center; margin: 2rem 0;">
                <h2 style="color: white; margin: 0;">Sistema Lotérica & Caixa Interno</h2>
                <p style="color: #f0f0f0; margin: 0.5rem 0 0 0;">Faça login para continuar</p>
            </div>
            """, unsafe_allow_html=True)
            
            usuario = st.text_input("👤 Usuário", placeholder="Digite seu usuário")
            senha = st.text_input("🔒 Senha", type="password", placeholder="Digite sua senha")
            
            if st.button("🚀 Entrar", use_container_width=True):
                # Credenciais de acesso
                credenciais = {
                    "gerente123": {"senha": "senha123", "perfil": "Gerente", "acesso": ["caixa", "cofre", "loteria", "dashboard"]},
                    "caixa123": {"senha": "senha123", "perfil": "Operador Caixa", "acesso": ["caixa", "dashboard"]},
                    "loterica123": {"senha": "senha123", "perfil": "Operador Lotérica", "acesso": ["loteria", "dashboard"]}
                }
                
                if usuario in credenciais and credenciais[usuario]["senha"] == senha:
                    st.session_state.logado = True
                    st.session_state.usuario = usuario
                    st.session_state.perfil = credenciais[usuario]["perfil"]
                    st.session_state.acesso = credenciais[usuario]["acesso"]
                    st.success(f"✅ Login realizado com sucesso! Bem-vindo, {credenciais[usuario]['perfil']}!")
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos!")
        
        return False
    
    return True

def render_dashboard_caixa():
    st.header("📊 Dashboard - Caixa Interno")
    
    try:
        spreadsheet = conectar_google_sheets()
        dados = buscar_dados(spreadsheet, "Operacoes_Caixa")
        dados_normalizados = normalizar_dados_inteligente(dados)
        
        if not dados_normalizados:
            st.info("📝 Nenhuma operação registrada ainda.")
            return
        
        # Converter para DataFrame
        df = pd.DataFrame(dados_normalizados)
        
        # Converter coluna de data para datetime
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data'])
        
        # Calcular métricas
        saldo_atual = df['Valor_Liquido'].sum()
        
        # Operações de hoje
        hoje = obter_date_brasilia()
        if 'Data' in df.columns:
            df_hoje = df[df['Data'].dt.date == hoje]
        else:
            df_hoje = pd.DataFrame()
        
        valor_saque_hoje = df_hoje['Valor_Bruto'].sum() if not df_hoje.empty else Decimal('0')
        operacoes_hoje = len(df_hoje)
        
        # Status do caixa
        if to_float(saldo_atual) > 5000:
            status_caixa = "🟢 Normal"
            cor_status = "green"
        elif to_float(saldo_atual) > 2000:
            status_caixa = "🟡 Atenção"
            cor_status = "orange"
        else:
            status_caixa = "🔴 Baixo"
            cor_status = "red"
        
        # Cards de métricas - Primeira linha
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "💰 Saldo Atual",
                format_currency_br(saldo_atual),
                delta=None
            )
        
        with col2:
            # Total de cartões (débito + crédito)
            df_cartoes = df[df['Tipo_Operacao'].isin(['Saque Cartão Débito', 'Saque Cartão Crédito'])]
            total_cartoes = df_cartoes['Valor_Bruto'].sum() if not df_cartoes.empty else Decimal('0')
            st.metric(
                "💳 Total Cartões",
                format_currency_br(total_cartoes)
            )
        
        with col3:
            # Total de cheques
            df_cheques = df[df['Tipo_Operacao'].str.contains('Cheque', na=False)]
            total_cheques = df_cheques['Valor_Bruto'].sum() if not df_cheques.empty else Decimal('0')
            st.metric(
                "📄 Total Cheques",
                format_currency_br(total_cheques)
            )
        
        with col4:
            # Total geral (cartões + cheques)
            total_geral = to_decimal(total_cartoes) + to_decimal(total_cheques)
            st.metric(
                "📊 Total Geral",
                format_currency_br(total_geral)
            )
        
        # Cards de métricas - Segunda linha
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            st.metric(
                "📅 Saques Hoje",
                format_currency_br(valor_saque_hoje)
            )
        
        with col6:
            st.metric(
                "🔢 Operações Hoje",
                f"{operacoes_hoje}"
            )
        
        with col7:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, {cor_status}20, {cor_status}10); 
                        padding: 1rem; border-radius: 10px; text-align: center;">
                <h4 style="margin: 0; color: {cor_status};">{status_caixa}</h4>
                <p style="margin: 0; color: #666;">Status do Caixa</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col8:
            # Total de suprimentos
            df_suprimentos = df[df['Tipo_Operacao'] == 'Suprimento']
            total_suprimentos = df_suprimentos['Valor_Bruto'].sum() if not df_suprimentos.empty else Decimal('0')
            st.metric(
                "📦 Suprimentos",
                format_currency_br(total_suprimentos)
            )
        
        # Gráfico de operações dos últimos 7 dias
        st.markdown("---")
        st.subheader("📈 Resumo dos Últimos 7 Dias")
        
        # Filtrar últimos 7 dias
        data_limite = obter_datetime_brasilia() - timedelta(days=7)
        if 'Data' in df.columns:
            df_recente = df[df['Data'] >= data_limite]
        else:
            df_recente = df
        
        if not df_recente.empty:
            # Agrupar por data
            df_agrupado = df_recente.groupby(df_recente['Data'].dt.date)['Valor_Bruto'].sum().reset_index()
            df_agrupado.columns = ['Data', 'Total']
            
            # Criar gráfico
            fig = px.line(
                df_agrupado, 
                x='Data', 
                y='Total',
                title="Volume de Operações por Dia",
                labels={'Total': 'Valor Total (R$)', 'Data': 'Data'}
            )
            fig.update_traces(line_color='#667eea', line_width=3)
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_family="Inter"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 Dados insuficientes para gerar gráfico dos últimos 7 dias.")
        
        # Alertas de saldo baixo
        if to_float(saldo_atual) < 2000:
            st.error("🚨 **ALERTA:** Saldo do caixa está baixo! Considere fazer um suprimento.")
        elif to_float(saldo_atual) < 5000:
            st.warning("⚠️ **ATENÇÃO:** Saldo do caixa está em nível de atenção.")
    
    except Exception as e:
        st.error(f"❌ Erro ao carregar dashboard: {str(e)}")

def render_operacoes_caixa():
    st.header("💳 Operações do Caixa Interno")
    
    # Tabs para diferentes operações
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💳 Saque Cartão", 
        "📄 Troca de Cheques", 
        "📦 Suprimento Caixa", 
        "📋 Histórico",
        "📊 Fechamento Caixa Interno"
    ])
    
    
with tab1:
    st.markdown("### 💳 Saque com Cartão")

    with st.form("form_saque_cartao", clear_on_submit=False):
        operador_selecionado = st.selectbox("👤 Operador Responsável", 
            ["Bruna", "Karina", "Edson", "Robson", "Adiel", "Lucas", "Ana Paula", "Fernanda"])

        col1, col2 = st.columns(2)
        with col1:
            tipo_cartao = st.selectbox("Tipo de Cartão", ["Débito", "Crédito"])
            valor = st.number_input("Valor do Saque (R$)", min_value=0.01, step=50.0)
            nome = st.text_input("Nome do Cliente (Opcional)")

        with col2:
            cpf = st.text_input("CPF do Cliente (Opcional)")
            observacoes = st.text_area("Observações")

        col_sim, col_conf = st.columns([1, 1])
        with col_sim:
            simular = st.form_submit_button("🧮 Simular Operação", use_container_width=True)

        if simular and valor > 0:
            try:
                valor_dec = Decimal(str(valor))
                if tipo_cartao == "Débito":
                    calc = calcular_taxa_cartao_debito(valor_dec)
                else:
                    calc = calcular_taxa_cartao_credito(valor_dec)

                st.markdown("---")
                st.markdown(f"### ✅ Simulação - Cartão {tipo_cartao}")

                col_res1, col_res2 = st.columns(2)
                with col_res1:
                    pct = (calc["taxa_cliente"] / valor_dec) * Decimal("100")
                    st.metric("Taxa Percentual", f"{float(pct):.2f}%")
                    st.metric("Taxa em Valores", f"R$ {float(calc['taxa_cliente']):,.2f}")
                with col_res2:
                    st.metric("💵 Valor a Entregar", f"R$ {float(calc['valor_liquido']):,.2f}")
                    st.info("💡 Taxa de 1% sobre o valor do saque" if tipo_cartao == "Débito" else "💡 Taxa de 5,33% sobre o valor do saque")

                st.session_state.simulacao_atual = {
                    "tipo": f"Saque Cartão {tipo_cartao}",
                    "dados": calc,
                    "valor_bruto": valor_dec,
                    "nome": nome or "Não informado",
                    "cpf": cpf or "Não informado",
                    "observacoes": observacoes
                }
            except Exception as e:
                st.error(f"❌ Erro na simulação: {str(e)}")

        with col_conf:
            confirmar = st.form_submit_button("💾 Confirmar e Salvar", use_container_width=True)
with tab2:
        render_troca_cheques()
    
    with tab3:
        render_suprimento_caixa()
    
    with tab4:
        render_historico_operacoes()
    
    with tab5:
        render_fechamento_caixa_interno()

def render_saque_cartao():
    st.subheader("💳 Saque com Cartão")
    
    with st.form("form_saque_cartao"):
        # Campo de operador
        operador = st.selectbox(
            "👤 Operador Responsável",
            ["Bruna", "Karina", "Edson", "Robson", "Adiel", "Lucas", "Ana Paula", "Fernanda"],
            key="operador_cartao"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            tipo_cartao = st.selectbox("Tipo de Cartão", ["Débito", "Crédito"])
            valor = st.number_input("Valor do Saque (R$)", min_value=0.01, value=100.00, step=0.01)
            nome_cliente = st.text_input("Nome do Cliente (Opcional)")
        
        with col2:
            cpf_cliente = st.text_input("CPF do Cliente (Opcional)")
            observacoes = st.text_area("Observações")
        
        col_sim, col_conf = st.columns(2)
        
        with col_sim:
            simular = st.form_submit_button("🧮 Simular Operação", use_container_width=True)
        
        with col_conf:
            confirmar = st.form_submit_button("💾 Confirmar e Salvar", use_container_width=True)
        
        if simular or confirmar:
            if tipo_cartao == "Débito":
                calc = calcular_taxa_cartao_debito(valor)
            else:
                calc = calcular_taxa_cartao_credito(valor)
            
            if simular:
                st.markdown(f"### ✅ Simulação - Cartão {tipo_cartao}")
                
                col_res1, col_res2 = st.columns(2)
                with col_res1:
                    st.metric("Taxa Percentual", safe_percentage(calc["taxa_cliente"], valor))
                    st.metric("Taxa em Valores", format_currency_br(calc["taxa_cliente"]))
                
                with col_res2:
                    st.metric("💵 Valor a Entregar", format_currency_br(calc["valor_liquido"]))
                    if tipo_cartao == "Débito":
                        st.info("💡 Taxa de 1% sobre o valor do saque")
                    else:
                        st.info("💡 Taxa de 5,33% sobre o valor do saque")
            
            if confirmar:
                try:
                    spreadsheet = conectar_google_sheets()
                    if spreadsheet:
                        worksheet = get_or_create_worksheet(
                            spreadsheet, 
                            "Operacoes_Caixa",
                            ["Data", "Hora", "Operador", "Tipo_Operacao", "Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Cliente", "CPF", "Observacoes"]
                        )
                        
                        # Preparar dados para salvar (formato americano para Google Sheets)
                        dados_salvar = [
                            obter_data_brasilia(),
                            obter_horario_brasilia(),
                            operador,
                            f"Saque Cartão {tipo_cartao}",
                            format_currency_us(valor),
                            format_currency_us(calc["taxa_cliente"]),
                            format_currency_us(calc["taxa_banco"]),
                            format_currency_us(calc["valor_liquido"]),
                            format_currency_us(calc["lucro"]),
                            nome_cliente,
                            cpf_cliente,
                            observacoes
                        ]
                        
                        worksheet.append_row(dados_salvar)
                        st.success("✅ Operação registrada com sucesso!")
                        
                        # Mostrar resumo
                        st.markdown(f"### 📋 Resumo da Operação")
                        st.info(f"""
                        **Tipo:** Saque Cartão {tipo_cartao}  
                        **Valor Bruto:** {format_currency_br(valor)}  
                        **Taxa:** {format_currency_br(calc["taxa_cliente"])}  
                        **Valor Líquido:** {format_currency_br(calc["valor_liquido"])}  
                        **Operador:** {operador}
                        """)
                    else:
                        st.warning("⚠️ Sem conexão com Google Sheets. Operação não foi salva.")
                
                except Exception as e:
                    st.error(f"❌ Erro ao salvar operação: {str(e)}")

def render_troca_cheques():
    st.subheader("📄 Troca de Cheques")
    
    with st.form("form_troca_cheques"):
        # Campo de operador
        operador = st.selectbox(
            "👤 Operador Responsável",
            ["Bruna", "Karina", "Edson", "Robson", "Adiel", "Lucas", "Ana Paula", "Fernanda"],
            key="operador_cheque"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            tipo_cheque = st.selectbox("Tipo de Cheque", ["Cheque à Vista", "Cheque Pré-datado", "Taxa Manual"])
            valor = st.number_input("Valor do Cheque (R$)", min_value=0.01, value=500.00, step=0.01)
            
            if tipo_cheque == "Cheque Pré-datado":
                dias = st.number_input("Dias até o vencimento", min_value=1, value=30, step=1)
            elif tipo_cheque == "Taxa Manual":
                taxa_manual = st.number_input("Taxa (%)", min_value=0.01, value=2.00, step=0.01)
            
            nome_cliente = st.text_input("Nome do Cliente (Opcional)")
        
        with col2:
            cpf_cliente = st.text_input("CPF do Cliente (Opcional)")
            observacoes = st.text_area("Observações")
        
        col_sim, col_conf = st.columns(2)
        
        with col_sim:
            simular = st.form_submit_button("🧮 Simular Operação", use_container_width=True)
        
        with col_conf:
            confirmar = st.form_submit_button("💾 Confirmar e Salvar", use_container_width=True)
        
        if simular or confirmar:
            if tipo_cheque == "Cheque à Vista":
                calc = calcular_taxa_cheque_vista(valor)
            elif tipo_cheque == "Cheque Pré-datado":
                calc = calcular_taxa_cheque_pre_datado(valor, dias)
            else:  # Taxa Manual
                calc = calcular_taxa_cheque_manual(valor, taxa_manual)
            
            if simular:
                st.markdown(f"### ✅ Simulação - {tipo_cheque}")
                
                col_res1, col_res2 = st.columns(2)
                with col_res1:
                    st.metric("Taxa Percentual", safe_percentage(calc["taxa_cliente"], valor))
                    st.metric("Taxa em Valores", format_currency_br(calc["taxa_cliente"]))
                
                with col_res2:
                    st.metric("💵 Valor a Entregar", format_currency_br(calc["valor_liquido"]))
                    if tipo_cheque == "Cheque à Vista":
                        st.info("💡 Taxa de 2% sobre o valor do cheque")
                    elif tipo_cheque == "Cheque Pré-datado":
                        taxa_total = 2 + (0.33 * dias)
                        st.info(f"💡 Taxa de {taxa_total:.2f}% (2% + 0,33% × {dias} dias)")
                    else:
                        st.info(f"💡 Taxa manual de {taxa_manual}%")
            
            if confirmar:
                try:
                    spreadsheet = conectar_google_sheets()
                    if spreadsheet:
                        worksheet = get_or_create_worksheet(
                            spreadsheet, 
                            "Operacoes_Caixa",
                            ["Data", "Hora", "Operador", "Tipo_Operacao", "Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Cliente", "CPF", "Observacoes"]
                        )
                        
                        # Preparar dados para salvar
                        tipo_operacao = tipo_cheque
                        if tipo_cheque == "Cheque Pré-datado":
                            tipo_operacao += f" ({dias} dias)"
                        elif tipo_cheque == "Taxa Manual":
                            tipo_operacao += f" ({taxa_manual}%)"
                        
                        dados_salvar = [
                            obter_data_brasilia(),
                            obter_horario_brasilia(),
                            operador,
                            tipo_operacao,
                            format_currency_us(valor),
                            format_currency_us(calc["taxa_cliente"]),
                            format_currency_us(calc["taxa_banco"]),
                            format_currency_us(calc["valor_liquido"]),
                            format_currency_us(calc["lucro"]),
                            nome_cliente,
                            cpf_cliente,
                            observacoes
                        ]
                        
                        worksheet.append_row(dados_salvar)
                        st.success("✅ Operação registrada com sucesso!")
                        
                        # Mostrar resumo
                        st.markdown(f"### 📋 Resumo da Operação")
                        st.info(f"""
                        **Tipo:** {tipo_operacao}  
                        **Valor Bruto:** {format_currency_br(valor)}  
                        **Taxa:** {format_currency_br(calc["taxa_cliente"])}  
                        **Valor Líquido:** {format_currency_br(calc["valor_liquido"])}  
                        **Operador:** {operador}
                        """)
                    else:
                        st.warning("⚠️ Sem conexão com Google Sheets. Operação não foi salva.")
                
                except Exception as e:
                    st.error(f"❌ Erro ao salvar operação: {str(e)}")

def render_suprimento_caixa():
    st.subheader("📦 Suprimento do Caixa")
    
    with st.form("form_suprimento"):
        # Campo de operador
        operador = st.selectbox(
            "👤 Operador Responsável",
            ["Bruna", "Karina", "Edson", "Robson", "Adiel", "Lucas", "Ana Paula", "Fernanda"],
            key="operador_suprimento"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            valor = st.number_input("Valor do Suprimento (R$)", min_value=0.01, value=1000.00, step=0.01)
            origem = st.selectbox("Origem do Suprimento", ["Cofre", "Banco", "Outros"])
        
        with col2:
            observacoes = st.text_area("Observações")
        
        col_sim, col_conf = st.columns(2)
        
        with col_sim:
            simular = st.form_submit_button("🧮 Simular Operação", use_container_width=True)
        
        with col_conf:
            confirmar = st.form_submit_button("💾 Confirmar e Salvar", use_container_width=True)
        
        if simular or confirmar:
            if simular:
                st.markdown("### ✅ Simulação - Suprimento")
                
                col_res1, col_res2 = st.columns(2)
                with col_res1:
                    st.metric("💰 Valor do Suprimento", format_currency_br(valor))
                    st.metric("📍 Origem", origem)
                
                with col_res2:
                    st.metric("💵 Valor a Adicionar ao Caixa", format_currency_br(valor))
                    st.info("💡 Suprimento não possui taxas")
            
            if confirmar:
                try:
                    spreadsheet = conectar_google_sheets()
                    if spreadsheet:
                        worksheet = get_or_create_worksheet(
                            spreadsheet, 
                            "Operacoes_Caixa",
                            ["Data", "Hora", "Operador", "Tipo_Operacao", "Valor_Bruto", "Taxa_Cliente", "Taxa_Banco", "Valor_Liquido", "Lucro", "Cliente", "CPF", "Observacoes"]
                        )
                        
                        dados_salvar = [
                            obter_data_brasilia(),
                            obter_horario_brasilia(),
                            operador,
                            f"Suprimento ({origem})",
                            format_currency_us(valor),
                            "0.00",  # Sem taxa
                            "0.00",  # Sem taxa banco
                            format_currency_us(valor),  # Valor líquido = valor bruto
                            "0.00",  # Sem lucro
                            "",  # Sem cliente
                            "",  # Sem CPF
                            observacoes
                        ]
                        
                        worksheet.append_row(dados_salvar)
                        st.success("✅ Suprimento registrado com sucesso!")
                        
                        # Mostrar resumo
                        st.markdown("### 📋 Resumo da Operação")
                        st.info(f"""
                        **Tipo:** Suprimento ({origem})  
                        **Valor:** {format_currency_br(valor)}  
                        **Operador:** {operador}
                        """)
                    else:
                        st.warning("⚠️ Sem conexão com Google Sheets. Operação não foi salva.")
                
                except Exception as e:
                    st.error(f"❌ Erro ao salvar suprimento: {str(e)}")

def render_historico_operacoes():
    st.subheader("📋 Histórico de Operações")
    
    try:
        spreadsheet = conectar_google_sheets()
        dados = buscar_dados(spreadsheet, "Operacoes_Caixa")
        dados_normalizados = normalizar_dados_inteligente(dados)
        
        if not dados_normalizados:
            st.info("📝 Nenhuma operação registrada ainda.")
            return
        
        # Converter para DataFrame
        df = pd.DataFrame(dados_normalizados)
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if 'Data' in df.columns:
                data_inicio = st.date_input("Data Início", value=obter_date_brasilia() - timedelta(days=30))
            else:
                data_inicio = obter_date_brasilia() - timedelta(days=30)
        
        with col2:
            if 'Data' in df.columns:
                data_fim = st.date_input("Data Fim", value=obter_date_brasilia())
            else:
                data_fim = obter_date_brasilia()
        
        with col3:
            if 'Tipo_Operacao' in df.columns:
                tipos_disponiveis = ["Todos"] + list(df['Tipo_Operacao'].unique())
                tipo_filtro = st.selectbox("Tipo de Operação", tipos_disponiveis)
            else:
                tipo_filtro = "Todos"
        
        # Aplicar filtros
        df_filtrado = df.copy()
        
        if 'Data' in df.columns:
            df_filtrado['Data'] = pd.to_datetime(df_filtrado['Data'])
            df_filtrado = df_filtrado[
                (df_filtrado['Data'].dt.date >= data_inicio) & 
                (df_filtrado['Data'].dt.date <= data_fim)
            ]
        
        if tipo_filtro != "Todos" and 'Tipo_Operacao' in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado['Tipo_Operacao'] == tipo_filtro]
        
        if not df_filtrado.empty:
            # Formatar valores para exibição
            df_exibicao = df_filtrado.copy()
            
            # Formatar colunas monetárias
            colunas_monetarias = ['Valor_Bruto', 'Taxa_Cliente', 'Taxa_Banco', 'Valor_Liquido', 'Lucro']
            for col in colunas_monetarias:
                if col in df_exibicao.columns:
                    df_exibicao[col] = df_exibicao[col].apply(format_currency_br)
            
            # Reordenar colunas para melhor visualização
            colunas_ordem = ['Data', 'Hora', 'Operador', 'Tipo_Operacao', 'Valor_Bruto', 'Taxa_Cliente', 'Valor_Liquido', 'Cliente']
            colunas_existentes = [col for col in colunas_ordem if col in df_exibicao.columns]
            
            st.dataframe(
                df_exibicao[colunas_existentes].sort_values('Data', ascending=False) if 'Data' in df_exibicao.columns else df_exibicao,
                use_container_width=True,
                hide_index=True
            )
            
            # Resumo do período
            st.markdown("---")
            st.subheader("📊 Resumo do Período")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_operacoes = len(df_filtrado)
                st.metric("🔢 Total de Operações", f"{total_operacoes}")
            
            with col2:
                valor_total = df_filtrado['Valor_Bruto'].sum()
                st.metric("💰 Valor Total", format_currency_br(valor_total))
            
            with col3:
                taxa_total = df_filtrado['Taxa_Cliente'].sum()
                st.metric("💸 Total em Taxas", format_currency_br(taxa_total))
            
            with col4:
                valor_liquido_total = df_filtrado['Valor_Liquido'].sum()
                st.metric("💵 Total Líquido", format_currency_br(valor_liquido_total))
        
        else:
            st.info("📝 Nenhuma operação encontrada para os filtros selecionados.")
    
    except Exception as e:
        st.error(f"❌ Erro ao carregar histórico: {str(e)}")

def render_fechamento_caixa_interno():
    st.subheader("📊 Fechamento do Caixa Interno")
    
    try:
        spreadsheet = conectar_google_sheets()
        dados = buscar_dados(spreadsheet, "Operacoes_Caixa")
        dados_normalizados = normalizar_dados_inteligente(dados)
        
        if not dados_normalizados:
            st.info("📝 Nenhuma operação registrada ainda.")
            return
        
        # Converter para DataFrame
        df = pd.DataFrame(dados_normalizados)
        
        # Seleção da data para fechamento
        data_fechamento = st.date_input("📅 Data do Fechamento", value=obter_date_brasilia())
        
        if 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data'])
            df_dia = df[df['Data'].dt.date == data_fechamento]
        else:
            df_dia = df
        
        if df_dia.empty:
            st.info(f"📝 Nenhuma operação encontrada para {data_fechamento.strftime('%d/%m/%Y')}.")
            return
        
        st.markdown(f"### 📋 Fechamento do dia {data_fechamento.strftime('%d/%m/%Y')}")
        
        # Separar por tipo de operação
        tipos_saque_cartao = ["Saque Cartão Débito", "Saque Cartão Crédito"]
        tipos_troca_cheque = ["Cheque à Vista", "Cheque Pré-datado"]
        
        # Ajustar para nomes que podem estar na planilha
        df_cartoes = df_dia[df_dia['Tipo_Operacao'].str.contains('Cartão', na=False)]
        df_cheques = df_dia[df_dia['Tipo_Operacao'].str.contains('Cheque', na=False)]
        df_suprimentos = df_dia[df_dia['Tipo_Operacao'].str.contains('Suprimento', na=False)]
        
        # Calcular totais
        total_cartoes = df_cartoes['Valor_Bruto'].sum() if not df_cartoes.empty else Decimal('0')
        total_cheques = df_cheques['Valor_Bruto'].sum() if not df_cheques.empty else Decimal('0')
        total_suprimentos = df_suprimentos['Valor_Bruto'].sum() if not df_suprimentos.empty else Decimal('0')
        
        # Exibir resumo
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### 💳 Saques com Cartão")
            st.metric("Total Saques Cartão", format_currency_br(total_cartoes))
            st.metric("Operações", f"{len(df_cartoes)}")
        
        with col2:
            st.markdown("#### 📄 Trocas de Cheque")
            st.metric("Total Trocas Cheque", format_currency_br(total_cheques))
            st.metric("Operações", f"{len(df_cheques)}")
        
        with col3:
            st.markdown("#### 📦 Suprimentos")
            st.metric("Total Suprimentos", format_currency_br(total_suprimentos))
            st.metric("Operações", f"{len(df_suprimentos)}")
        
        # Resumo geral
        st.markdown("---")
        st.markdown("#### 📊 Resumo Geral do Dia")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_operacoes = len(df_dia)
            st.metric("🔢 Total Operações", f"{total_operacoes}")
        
        with col2:
            total_movimentacao = total_cartoes + total_cheques + total_suprimentos
            st.metric("💰 Total Movimentação", format_currency_br(total_movimentacao))
        
        with col3:
            total_taxas = df_dia['Taxa_Cliente'].sum()
            st.metric("💸 Total Taxas", format_currency_br(total_taxas))
        
        with col4:
            saldo_final = df_dia['Valor_Liquido'].sum()
            st.metric("💵 Saldo Final", format_currency_br(saldo_final))
        
        # Detalhamento por operador
        if 'Operador' in df_dia.columns:
            st.markdown("---")
            st.markdown("#### 👥 Detalhamento por Operador")
            
            resumo_operadores = df_dia.groupby('Operador').agg({
                'Valor_Bruto': 'sum',
                'Taxa_Cliente': 'sum',
                'Valor_Liquido': 'sum',
                'Tipo_Operacao': 'count'
            }).round(2)
            
            resumo_operadores.columns = ['Total Bruto', 'Total Taxas', 'Total Líquido', 'Qtd Operações']
            
            # Formatar valores
            for col in ['Total Bruto', 'Total Taxas', 'Total Líquido']:
                resumo_operadores[col] = resumo_operadores[col].apply(format_currency_br)
            
            st.dataframe(resumo_operadores, use_container_width=True)
    
    except Exception as e:
        st.error(f"❌ Erro ao gerar fechamento: {str(e)}")

def render_cofre():
    st.header("🏦 Gestão do Cofre")
    
    # Inicializar session_state para campos dinâmicos
    if "tipo_movimentacao" not in st.session_state:
        st.session_state.tipo_movimentacao = "Entrada no Cofre"
    
    # Seleção do tipo de movimentação
    tipo_movimentacao = st.selectbox(
        "Tipo de Movimentação",
        ["Entrada no Cofre", "Saída do Cofre"],
        key="select_tipo_movimentacao"
    )
    
    # Atualizar session_state quando houver mudança
    if st.session_state.tipo_movimentacao != tipo_movimentacao:
        st.session_state.tipo_movimentacao = tipo_movimentacao
        st.rerun()
    
    with st.form("form_cofre"):
        col1, col2 = st.columns(2)
        
        with col1:
            valor = st.number_input("Valor (R$)", min_value=0.01, value=1000.00, step=0.01)
            
            if st.session_state.tipo_movimentacao == "Entrada no Cofre":
                origem = st.selectbox("Origem da Entrada", ["Caixa Interno", "Banco", "Vendas Lotérica", "Outros"])
            else:  # Saída do Cofre
                tipo_saida = st.selectbox("Tipo de Saída", ["Transferência para Caixa", "Pagamento de Despesa", "Outros"])
                
                if tipo_saida == "Transferência para Caixa":
                    destino = st.selectbox("Destino do Caixa", ["Caixa Interno", "Caixa Lotérica"])
                elif tipo_saida == "Pagamento de Despesa":
                    descricao_despesa = st.text_input("Descrição da Despesa")
                else:
                    outros_destino = st.text_input("Especificar Destino")
        
        with col2:
            responsavel = st.text_input("Responsável pela Operação")
            observacoes = st.text_area("Observações")
        
        col_sim, col_conf = st.columns(2)
        
        with col_sim:
            simular = st.form_submit_button("🧮 Simular Operação", use_container_width=True)
        
        with col_conf:
            confirmar = st.form_submit_button("💾 Confirmar e Salvar", use_container_width=True)
        
        if simular or confirmar:
            if simular:
                st.markdown(f"### ✅ Simulação - {st.session_state.tipo_movimentacao}")
                
                col_res1, col_res2 = st.columns(2)
                with col_res1:
                    st.metric("💰 Valor", format_currency_br(valor))
                    if st.session_state.tipo_movimentacao == "Entrada no Cofre":
                        st.metric("📍 Origem", origem)
                    else:
                        st.metric("📍 Tipo", tipo_saida)
                
                with col_res2:
                    if st.session_state.tipo_movimentacao == "Entrada no Cofre":
                        st.metric("➕ Valor a Adicionar", format_currency_br(valor))
                    else:
                        st.metric("➖ Valor a Retirar", format_currency_br(valor))
                    st.metric("👤 Responsável", responsavel)
            
            if confirmar:
                try:
                    spreadsheet = conectar_google_sheets()
                    if spreadsheet:
                        worksheet = get_or_create_worksheet(
                            spreadsheet, 
                            "Operacoes_Cofre",
                            ["Data", "Hora", "Tipo_Movimentacao", "Valor", "Origem_Destino", "Responsavel", "Observacoes"]
                        )
                        
                        # Determinar origem/destino
                        if st.session_state.tipo_movimentacao == "Entrada no Cofre":
                            origem_destino = origem
                        else:
                            if tipo_saida == "Transferência para Caixa":
                                origem_destino = f"Transferência para {destino}"
                            elif tipo_saida == "Pagamento de Despesa":
                                origem_destino = f"Despesa: {descricao_despesa}"
                            else:
                                origem_destino = f"Outros: {outros_destino}"
                        
                        dados_salvar = [
                            obter_data_brasilia(),
                            obter_horario_brasilia(),
                            st.session_state.tipo_movimentacao,
                            format_currency_us(valor),
                            origem_destino,
                            responsavel,
                            observacoes
                        ]
                        
                        worksheet.append_row(dados_salvar)
                        st.success("✅ Movimentação registrada com sucesso!")
                        
                        # Mostrar resumo
                        st.markdown("### 📋 Resumo da Operação")
                        st.info(f"""
                        **Tipo:** {st.session_state.tipo_movimentacao}  
                        **Valor:** {format_currency_br(valor)}  
                        **Origem/Destino:** {origem_destino}  
                        **Responsável:** {responsavel}
                        """)
                    else:
                        st.warning("⚠️ Sem conexão com Google Sheets. Operação não foi salva.")
                
                except Exception as e:
                    st.error(f"❌ Erro ao salvar movimentação: {str(e)}")

def render_loteria():
    st.header("🎰 Fechamento da Lotérica")
    
    # Seleção do PDV
    pdv = st.selectbox("Selecione o PDV", ["PDV1", "PDV2"])
    
    with st.form(f"form_fechamento_{pdv}"):
        st.subheader(f"📊 Fechamento {pdv}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🎯 Bolão")
            bolao_compra = st.number_input("Compra Bolão (R$)", min_value=0.00, value=0.00, step=0.01, key=f"bolao_compra_{pdv}")
            bolao_venda = st.number_input("Venda Bolão (R$)", min_value=0.00, value=0.00, step=0.01, key=f"bolao_venda_{pdv}")
            
            st.markdown("#### 🎫 Raspadinha")
            raspadinha_compra = st.number_input("Compra Raspadinha (R$)", min_value=0.00, value=0.00, step=0.01, key=f"raspadinha_compra_{pdv}")
            raspadinha_venda = st.number_input("Venda Raspadinha (R$)", min_value=0.00, value=0.00, step=0.01, key=f"raspadinha_venda_{pdv}")
        
        with col2:
            st.markdown("#### 🎲 Loteria Federal")
            federal_compra = st.number_input("Compra Federal (R$)", min_value=0.00, value=0.00, step=0.01, key=f"federal_compra_{pdv}")
            federal_venda = st.number_input("Venda Federal (R$)", min_value=0.00, value=0.00, step=0.01, key=f"federal_venda_{pdv}")
            
            st.markdown("#### 💰 Movimentações")
            entrada_dinheiro = st.number_input("Entrada de Dinheiro (R$)", min_value=0.00, value=0.00, step=0.01, key=f"entrada_{pdv}")
            saida_dinheiro = st.number_input("Saída de Dinheiro (R$)", min_value=0.00, value=0.00, step=0.01, key=f"saida_{pdv}")
        
        observacoes = st.text_area("Observações", key=f"obs_{pdv}")
        
        if st.form_submit_button("💾 Salvar Fechamento", use_container_width=True):
            try:
                # Calcular diferenças
                dif_bolao = to_decimal(bolao_venda) - to_decimal(bolao_compra)
                dif_raspadinha = to_decimal(raspadinha_venda) - to_decimal(raspadinha_compra)
                dif_federal = to_decimal(federal_venda) - to_decimal(federal_compra)
                
                total_vendas = to_decimal(bolao_venda) + to_decimal(raspadinha_venda) + to_decimal(federal_venda)
                total_compras = to_decimal(bolao_compra) + to_decimal(raspadinha_compra) + to_decimal(federal_compra)
                resultado_liquido = total_vendas - total_compras
                
                spreadsheet = conectar_google_sheets()
                if spreadsheet:
                    worksheet = get_or_create_worksheet(
                        spreadsheet, 
                        f"Fechamentos_{pdv}",
                        ["Data", "Hora", "Bolao_Compra", "Bolao_Venda", "Bolao_Diferenca", 
                         "Raspadinha_Compra", "Raspadinha_Venda", "Raspadinha_Diferenca",
                         "Federal_Compra", "Federal_Venda", "Federal_Diferenca",
                         "Entrada_Dinheiro", "Saida_Dinheiro", "Total_Vendas", "Total_Compras", 
                         "Resultado_Liquido", "Observacoes"]
                    )
                    
                    dados_salvar = [
                        obter_data_brasilia(),
                        obter_horario_brasilia(),
                        format_currency_us(bolao_compra),
                        format_currency_us(bolao_venda),
                        format_currency_us(dif_bolao),
                        format_currency_us(raspadinha_compra),
                        format_currency_us(raspadinha_venda),
                        format_currency_us(dif_raspadinha),
                        format_currency_us(federal_compra),
                        format_currency_us(federal_venda),
                        format_currency_us(dif_federal),
                        format_currency_us(entrada_dinheiro),
                        format_currency_us(saida_dinheiro),
                        format_currency_us(total_vendas),
                        format_currency_us(total_compras),
                        format_currency_us(resultado_liquido),
                        observacoes
                    ]
                    
                    worksheet.append_row(dados_salvar)
                    st.success(f"✅ Fechamento {pdv} registrado com sucesso!")
                    
                    # Mostrar resumo
                    st.markdown(f"### 📋 Resumo do Fechamento {pdv}")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("🎯 Resultado Bolão", format_currency_br(dif_bolao))
                        st.metric("🎫 Resultado Raspadinha", format_currency_br(dif_raspadinha))
                    
                    with col2:
                        st.metric("🎲 Resultado Federal", format_currency_br(dif_federal))
                        st.metric("💰 Total Vendas", format_currency_br(total_vendas))
                    
                    with col3:
                        st.metric("💸 Total Compras", format_currency_br(total_compras))
                        st.metric("📊 Resultado Líquido", format_currency_br(resultado_liquido))
                else:
                    st.warning("⚠️ Sem conexão com Google Sheets. Fechamento não foi salvo.")
            
            except Exception as e:
                st.error(f"❌ Erro ao salvar fechamento: {str(e)}")

# Função principal
def main():
    if not verificar_login():
        return
    
    # Sidebar com navegação
    st.sidebar.title("🏧 Sistema Unificado")
    st.sidebar.markdown(f"**Usuário:** {st.session_state.perfil}")
    
    # Menu baseado no perfil do usuário
    opcoes_menu = []
    
    if "dashboard" in st.session_state.acesso:
        opcoes_menu.append("📊 Dashboard")
    
    if "caixa" in st.session_state.acesso:
        opcoes_menu.append("💳 Operações do Caixa Interno")
    
    if "cofre" in st.session_state.acesso:
        opcoes_menu.append("🏦 Gestão do Cofre")
    
    if "loteria" in st.session_state.acesso:
        opcoes_menu.append("🎰 Fechamento Lotérica")
    
    opcao = st.sidebar.selectbox("Navegação", opcoes_menu)
    
    # Botão de logout
    if st.sidebar.button("🚪 Sair"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    # Renderizar página selecionada
    if opcao == "📊 Dashboard":
        render_dashboard_caixa()
    elif opcao == "💳 Operações do Caixa Interno":
        render_operacoes_caixa()
    elif opcao == "🏦 Gestão do Cofre":
        render_cofre()
    elif opcao == "🎰 Fechamento Lotérica":
        render_loteria()

if __name__ == "__main__":
    main()

