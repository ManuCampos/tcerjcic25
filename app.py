import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import io
import re
import requests

# Configuração da página
st.set_page_config(
    page_title="Projeto Predição de Editais - CIC2025",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado para interface profissional
st.markdown("""
<style>
    /* Tema principal */
    .main-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .main-header h1 {
        color: white;
        margin: 0;
        font-weight: 600;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #3b82f6;
        margin: 0.5rem 0;
    }
    
    .filter-section {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .alert-info {
        background: #dbeafe;
        border: 1px solid #3b82f6;
        color: #1e40af;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .alert-success {
        background: #dcfce7;
        border: 1px solid #16a34a;
        color: #15803d;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .alert-warning {
        background: #fef3c7;
        border: 1px solid #f59e0b;
        color: #92400e;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .sidebar .sidebar-content {
        background: #f1f5f9;
    }
    
    /* Estilo para métricas */
    .metric-container {
        display: flex;
        flex-wrap: wrap;
        gap: 1rem;
        margin: 1rem 0;
    }
    
    /* Botões personalizados */
    .stButton > button {
        background: linear-gradient(90deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
    }
    
    /* Estilo para selectbox */
    .stSelectbox > div > div {
        border-radius: 8px;
    }
    
    /* Tabelas */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* Loading spinner personalizado */
    .loading-container {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# URL do SharePoint (pode precisar de autenticação)
SHAREPOINT_URL = "https://tcerj365-my.sharepoint.com/:x:/g/personal/emanuellipc_tcerj_tc_br/EapYf2FOUAZKhwemlND9-yABORDNXmUQrevxWZHffU2wSg?e=gwyMcP"
# Tentativa de conversão para download direto
SHAREPOINT_CSV_URL = "https://tcerj365-my.sharepoint.com/:x:/g/personal/emanuellipc_tcerj_tc_br/EapYf2FOUAZKhwemlND9-yABORDNXmUQrevxWZHffU2wSg?e=gwyMcP&download=1"

@st.cache_data(ttl=300)  # Cache por 5 minutos
def load_data_from_sharepoint():
    """Carrega dados diretamente do SharePoint"""
    try:
        # Primeira tentativa - URL com download=1
        try:
            response = requests.get(SHAREPOINT_CSV_URL, timeout=30)
            response.raise_for_status()
        except:
            # Segunda tentativa - URL original
            response = requests.get(SHAREPOINT_URL, timeout=30)
            response.raise_for_status()
        
        # Primeiro, tenta o método padrão mais robusto
        try:
            df = pd.read_csv(
                io.StringIO(response.text),
                encoding='utf-8',
                sep=',',
                quotechar='"',
                escapechar='\\',
                on_bad_lines='skip',  # Pula linhas problemáticas
                engine='python',  # Engine mais tolerante
                dtype=str,  # Carrega tudo como string primeiro
                low_memory=False
            )
        except Exception as e1:
            # Método alternativo - tenta com delimitador automático
            try:
                df = pd.read_csv(
                    io.StringIO(response.text),
                    sep=None,  # Detecta automaticamente o delimitador
                    engine='python',
                    encoding='utf-8',
                    on_bad_lines='skip',
                    dtype=str
                )
            except Exception as e2:
                # Último recurso - verifica se é HTML (página de login)
                if "<html" in response.text.lower() or "sign in" in response.text.lower():
                    return None, "SharePoint requer autenticação - use upload manual ou configure permissões públicas"
                
                return None, f"Erro de parsing: {str(e1)}. Tentativa alternativa: {str(e2)}"
        
        # Remove linhas completamente vazias
        df = df.dropna(how='all')
        
        # Remove colunas que são completamente vazias ou têm nomes inválidos
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df = df.dropna(axis=1, how='all')
        
        # Conversões de tipos mais seguras
        if 'data realizacao licitacao' in df.columns:
            df['data realizacao licitacao'] = pd.to_datetime(df['data realizacao licitacao'], errors='coerce')
        
        if 'ano' in df.columns:
            df['ano'] = pd.to_numeric(df['ano'], errors='coerce')
        
        if 'valor estimado' in df.columns:
            # Remove caracteres não numéricos exceto pontos e vírgulas
            df['valor estimado'] = df['valor estimado'].astype(str).str.replace(r'[^\d.,]', '', regex=True)
            df['valor estimado'] = df['valor estimado'].str.replace(',', '.', regex=False)
            df['valor estimado'] = pd.to_numeric(df['valor estimado'], errors='coerce')
        
        if 'pontuacao' in df.columns:
            df['pontuacao'] = df['pontuacao'].astype(str).str.replace(',', '.', regex=False)
            df['pontuacao'] = pd.to_numeric(df['pontuacao'], errors='coerce')
            
        if 'pontuacao_final' in df.columns:
            df['pontuacao_final'] = df['pontuacao_final'].astype(str).str.replace(',', '.', regex=False)
            df['pontuacao_final'] = pd.to_numeric(df['pontuacao_final'], errors='coerce')
        
        # Processamento da coluna observacoes - preenche valores em branco
        if 'observacoes' in df.columns:
            df['observacoes'] = df['observacoes'].apply(
                lambda x: x if pd.notna(x) and str(x).strip() != '' else 'Classificação baseada em Termos Chave'
            )
        
        # Renomeação de colunas específicas
        column_renames = {
            'classificacao_final - Copiar': 'Predição CIC',
            'predicao classificacao': 'Predição STI'
        }
        
        for old_name, new_name in column_renames.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # Remoção de duplicatas ignorando a coluna 'classificacao_final'
        columns_for_dedup = [col for col in df.columns if col != 'classificacao_final']
        if columns_for_dedup:
            df = df.drop_duplicates(subset=columns_for_dedup, keep='first')
        
        # Processamento da coluna observacoes - preenche valores em branco
        if 'observacoes' in df.columns:
            df['observacoes'] = df['observacoes'].apply(
                lambda x: x if pd.notna(x) and str(x).strip() != '' else 'Classificação baseada em Termos Chave'
            )
        
        # Validação final - se o dataframe está vazio ou muito pequeno
        if len(df) == 0:
            return None, "Nenhum dado válido encontrado na planilha"
        
        if len(df.columns) < 5:
            return None, "Estrutura de dados incompleta - muito poucas colunas"
            
        return df, None
        
    except requests.exceptions.RequestException as e:
        if "403" in str(e) or "401" in str(e):
            return None, "Acesso negado - SharePoint requer permissões ou autenticação"
        return None, f"Erro de conexão: {str(e)}"
    except pd.errors.EmptyDataError:
        return None, "Planilha está vazia ou não contém dados válidos"
    except pd.errors.ParserError as e:
        return None, f"Erro de formatação dos dados: {str(e)}"
    except Exception as e:
        return None, f"Erro inesperado: {str(e)}"

def create_overview_metrics(df):
    """Cria métricas de visão geral com dados fixos da base completa"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📋 Total de Editais",
            value="52.429",
            delta=None
        )
    
    with col2:
        st.metric(
            label="💰 Valor Total Estimado",
            value="R$ 244 Bilhões",
            delta=None
        )
    
    with col3:
        st.metric(
            label="🏷️ Categorias Únicas",
            value="14",
            delta=None
        )
    
    with col4:
        st.metric(
            label="🏢 Unidades Únicas",
            value="729",
            delta=None
        )

def apply_filters(df, search_term, filters):
    """Aplica os filtros ao dataframe com tratamento melhorado de erros"""
    filtered_df = df.copy()
    
    # Aplicar busca por termo livre (suporte a múltiplos termos separados por ;)
    if search_term:
        search_columns = ['objeto', 'unidade', 'observacoes', 'todos_termos', 'descricao situacao edital', 'objeto_processada']
        # Filtra apenas colunas que existem no DataFrame
        search_columns = [col for col in search_columns if col in df.columns]
        
        if search_columns:  # Só procede se houver colunas para buscar
            # Verifica se há múltiplos termos separados por ponto e vírgula
            if ';' in search_term:
                search_terms = [term.strip().lower() for term in search_term.split(';') if term.strip()]
                
                # Cria máscara para buscar qualquer um dos termos (OR logic)
                mask = pd.Series(False, index=filtered_df.index)
                for term in search_terms:
                    term_mask = pd.Series(False, index=filtered_df.index)
                    for col in search_columns:
                        # Converte a coluna para string e trata valores nulos
                        term_mask |= filtered_df[col].fillna('').astype(str).str.lower().str.contains(term, na=False)
                    mask |= term_mask
                
                filtered_df = filtered_df[mask]
            else:
                # Busca por termo único
                mask = pd.Series(False, index=filtered_df.index)
                search_term = search_term.lower().strip()
                for col in search_columns:
                    # Converte a coluna para string e trata valores nulos
                    mask |= filtered_df[col].fillna('').astype(str).str.lower().str.contains(search_term, na=False)
                filtered_df = filtered_df[mask]
    
    # Aplicar filtros específicos
    for column, value in filters.items():
        if value not in ['Todas', 'Todos'] and column in filtered_df.columns:
            if column == 'valor_range':
                min_val, max_val = value
                filtered_df = filtered_df[
                    (filtered_df['valor estimado'].fillna(0).astype(float) >= min_val) & 
                    (filtered_df['valor estimado'].fillna(0).astype(float) <= max_val)
                ]
            elif column == 'ano':
                # Trata o ano como número
                filtered_df = filtered_df[filtered_df[column].fillna(0).astype(float) == float(value)]
            else:
                # Para outros campos, faz comparação de strings
                filtered_df = filtered_df[filtered_df[column].fillna('').astype(str) == str(value)]
    
    return filtered_df

def create_charts(df):
    """Cria gráficos de análise"""
    col1, col2 = st.columns(2)
    
    with col1:
        if 'unidade' in df.columns and len(df) > 0:
            # Gráfico de quantidade de editais por coordenadoria
            unidade_counts = df['unidade'].value_counts().head(10)
            
            if len(unidade_counts) > 0:
                fig_bar = px.bar(
                    x=unidade_counts.values,
                    y=unidade_counts.index,
                    orientation='h',
                    title="📊 Quantidade de Editais por Coordenadoria",
                    labels={'x': 'Quantidade', 'y': 'Coordenadoria'},
                    color=unidade_counts.values,
                    color_continuous_scale='Blues'
                )
                fig_bar.update_layout(
                    height=400,
                    showlegend=False,
                    yaxis={'categoryorder': 'total ascending'}
                )
                st.plotly_chart(fig_bar, use_container_width=True)
    
    with col2:
        if 'unidade' in df.columns and 'valor estimado' in df.columns and len(df) > 0:
            # Gráfico das maiores coordenadorias por valor estimado
            unidade_valores = df.groupby('unidade')['valor estimado'].sum().sort_values(ascending=False).head(8)
            
            if len(unidade_valores) > 0:
                fig_pie = px.pie(
                    values=unidade_valores.values,
                    names=unidade_valores.index,
                    title="💰 Maiores Coordenadorias por Valor Estimado"
                )
                fig_pie.update_layout(height=400)
                st.plotly_chart(fig_pie, use_container_width=True)
    
    # Gráfico temporal se houver dados de data
    if 'ano' in df.columns and len(df) > 0:
        st.markdown("### 📈 Evolução Temporal")
        temporal_data = df['ano'].value_counts().sort_index()
        
        if len(temporal_data) > 0:
            fig_line = px.line(
                x=temporal_data.index,
                y=temporal_data.values,
                title="Editais por Ano",
                labels={'x': 'Ano', 'y': 'Quantidade de Editais'},
                markers=True
            )
            fig_line.update_layout(height=400)
            st.plotly_chart(fig_line, use_container_width=True)

def display_data_table(df):
    """Exibe a tabela de dados com opções de visualização"""
    st.markdown("### 📋 Dados dos Editais")
    
    # Opções de visualização
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        # Colunas padrão específicas atualizadas com novos nomes
        default_columns = []
        preferred_columns = ['Predição CIC', 'Predição STI', 'unidade', 'objeto', 'valor estimado', 'observacoes', 'todos_termos']
        for col in preferred_columns:
            if col in df.columns:
                default_columns.append(col)
        
        # Se não encontrou nenhuma das preferidas, usa as primeiras 5 colunas
        if len(default_columns) == 0:
            default_columns = df.columns.tolist()[:5]
        
        columns_to_show = st.multiselect(
            "📊 Selecionar colunas para exibir",
            options=df.columns.tolist(),
            default=default_columns
        )
    
    with col2:
        rows_per_page = st.selectbox(
            "📄 Linhas por página",
            [10, 25, 50, 100],
            index=1
        )
    
    with col3:
        export_button = st.button("📥 Exportar Filtrados")
    
    if columns_to_show:
        # Paginação
        total_rows = len(df)
        total_pages = (total_rows - 1) // rows_per_page + 1
        
        if total_pages > 1:
            page = st.number_input(
                f"Página (1 de {total_pages})",
                min_value=1,
                max_value=total_pages,
                value=1
            ) - 1
        else:
            page = 0
        
        start_idx = page * rows_per_page
        end_idx = start_idx + rows_per_page
        
        # Exibir dados
        display_df = df[columns_to_show].iloc[start_idx:end_idx].copy()
        
        # Formatação condicional para valores monetários
        if 'valor estimado' in display_df.columns:
            display_df['valor estimado'] = display_df['valor estimado'].apply(
                lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if pd.notna(x) else 'N/A'
            )
        
        # Formatação para pontuações
        for col in ['pontuacao', 'pontuacao_final']:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(
                    lambda x: f"{x:.2f}" if pd.notna(x) else 'N/A'
                )
        
        # Preenchimento automático para observações em branco
        if 'observacoes' in display_df.columns:
            display_df['observacoes'] = display_df['observacoes'].apply(
                lambda x: x if pd.notna(x) and str(x).strip() != '' else 'Classificação baseada em Termos Chave'
            )
        
        st.dataframe(
            display_df,
            use_container_width=True,
            height=400
        )
        
        # Informações da paginação
        st.info(f"Exibindo {start_idx + 1}-{min(end_idx, total_rows)} de {total_rows} registros")
        
        # Checkbox para mostrar apenas divergências
        if 'Predição CIC' in df.columns and 'Predição STI' in df.columns:
            show_only_divergences = st.checkbox(
                "📊 Exibir apenas divergências entre 'Predição CIC' e 'Predição STI'"
            )
            
            if show_only_divergences:
                # Filtra apenas as linhas onde as predições são diferentes
                divergent_df = df[df['Predição CIC'] != df['Predição STI']]
                
                if len(divergent_df) > 0:
                    st.markdown("### 🔍 Divergências Identificadas")
                    st.info(f"📋 Encontradas {len(divergent_df):,} divergências de {len(df):,} registros ({(len(divergent_df)/len(df)*100):.2f}%)")
                    
                    # Recalcula paginação para divergências
                    div_total_rows = len(divergent_df)
                    div_total_pages = (div_total_rows - 1) // rows_per_page + 1
                    
                    if div_total_pages > 1:
                        div_page = st.number_input(
                            f"Página de Divergências (1 de {div_total_pages})",
                            min_value=1,
                            max_value=div_total_pages,
                            value=1,
                            key="divergences_page"
                        ) - 1
                    else:
                        div_page = 0
                    
                    div_start_idx = div_page * rows_per_page
                    div_end_idx = div_start_idx + rows_per_page
                    
                    # Exibir dados de divergências
                    div_display_df = divergent_df[columns_to_show].iloc[div_start_idx:div_end_idx].copy()
                    
                    # Aplicar formatações
                    if 'valor estimado' in div_display_df.columns:
                        div_display_df['valor estimado'] = div_display_df['valor estimado'].apply(
                            lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if pd.notna(x) else 'N/A'
                        )
                    
                    if 'observacoes' in div_display_df.columns:
                        div_display_df['observacoes'] = div_display_df['observacoes'].apply(
                            lambda x: x if pd.notna(x) and str(x).strip() != '' else 'Classificação baseada em Termos Chave'
                        )
                    
                    st.dataframe(
                        div_display_df,
                        use_container_width=True,
                        height=400
                    )
                    
                    st.info(f"Exibindo {div_start_idx + 1}-{min(div_end_idx, div_total_rows)} de {div_total_rows} divergências")
                else:
                    st.success("✅ Nenhuma divergência encontrada! Todas as predições estão alinhadas.")
        
        # Funcionalidade de exportação
        if export_button:
            csv = df[columns_to_show].to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"editais_filtrados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

def show_help_tab():
    """Mostra a aba de ajuda e instruções"""
    st.markdown("""
    # 📚 Como Usar o Projeto Predição de Editais - CIC2025
    
    ## 🚀 Início Rápido
    
    ### 1. Escopo da Base de Dados
    - **52.429 editais** analisados e classificados
    - **R$ 244 bilhões** em valor total estimado
    - **729 coordenadorias/unidades** organizacionais mapeadas
    - **14 categorias originais** + **2 novas categorias** criadas
    - Sistema carrega amostras para consulta interativa
    
    ### 2. Dados Automáticos
    - Os dados são carregados automaticamente do SharePoint TCERJ
    - Sistema atualiza a cada 5 minutos para manter dados frescos
    - Não é necessário fazer upload manual (se configurado corretamente)
    
    ### 3. Navegação
    O sistema possui **3 abas principais**:
    - **📊 Análise de Dados**: Visualização principal com filtros e tabelas
    - **📈 Dashboard**: Gráficos e estatísticas detalhadas
    - **📚 Ajuda**: Esta seção com instruções
    
    ## 🔍 Funcionalidades de Pesquisa
    
    ### Busca por Termo Livre
    - Use a caixa "🔎 Buscar por termo" na barra lateral
    - Busca em múltiplas colunas: objeto, unidade, observações, todos os termos
    - **Busca múltipla**: Use ponto e vírgula (;) para buscar vários termos
    - **Exemplo**: "educação; saúde; infraestrutura" busca qualquer um dos termos
    - **Não diferencia maiúsculas de minúsculas**
    
    ### Exemplos de Busca Múltipla
    - **Por área temática**: "educação; ensino; escola"
    - **Por tipo de obra**: "construção; reforma; ampliação"
    - **Por localização**: "rio de janeiro; niterói; duque de caxias"
    - **Termos relacionados**: "hospital; posto de saúde; upa"
    
    ### Filtros Específicos
    - **📂 Nova Classificação**: Filtra pela classificação final atualizada
    - **🔮 Predição CIC**: Filtra pela predição da Coordenadoria de Informações Estratégicas
    - **🔄 Predição STI**: Filtra pela predição original da Secretaria de Tecnologia da Informação
    - **🏢 Unidade**: Filtra por coordenadoria/unidade específica
    - **📋 Modalidade**: Filtra por tipo de modalidade licitatória
    - **📅 Ano**: Filtra por ano específico
    - **💰 Valor**: Use o slider para definir faixa de valores
    
    ## 📊 Visualizações Disponíveis
    
    ### Métricas Principais
    - **Total de Editais**: 52.429 editais na base completa
    - **Valor Total Estimado**: R$ 244 bilhões em investimentos
    - **Categorias Únicas**: 14 categorias de classificação
    - **Unidades Únicas**: 729 coordenadorias/unidades mapeadas
    
    ### Análise de Categorização
    - **Editais Complexos**: 8.574 editais em múltiplas categorias (16,35%)
    - **Editais Simples**: 43.855 editais em categoria única (83,65%)
    - **Mudanças nas Predições**: Percentual de casos onde Predição CIC difere da Predição STI
    - **Qualidade da Base**: Maioria com classificação única (mais confiável)
    - **Desafio de Classificação**: 1 em cada 6 editais tem múltiplas categorias
    - **Análise de Divergências**: Checkbox para visualizar apenas casos com predições diferentes
    
    ### Gráficos Interativos
    - **Quantidade por Coordenadoria**: Barras horizontais com ranking de unidades
    - **Maiores Coordenadorias**: Gráfico de pizza por valor estimado
    - **Evolução Temporal**: Linha do tempo com tendências anuais
    
    ## 📋 Tabela de Dados
    
    ### Personalização da Visualização
    - **Colunas Padrão**: Predição CIC, Predição STI, Unidade, Objeto, Valor Estimado, Observações, Todos os Termos
    - **Seleção Personalizada**: Escolha quais campos exibir conforme necessidade
    - **Paginação**: Configure quantas linhas ver por página (10, 25, 50, 100)
    - **Exportação**: Baixe os dados filtrados em CSV
    - **Análise de Divergências**: Checkbox para mostrar apenas casos onde as predições diferem
    - **Observações Automáticas**: Campos em branco são preenchidos automaticamente com "Classificação baseada em Termos Chave"
    
    ### Formatação Inteligente
    - Valores monetários formatados automaticamente (R$ 1.234.567,89)
    - Datas em formato brasileiro
    - Navegação intuitiva entre páginas
    - Preenchimento automático de observações em branco
    - Remoção automática de duplicatas (ignorando coluna classificacao_final)
    
    ## 💡 Dicas de Uso
    
    ### Para Gestores CIC
    1. **Análise Comparativa**: Compare Predição CIC vs Predição STI para avaliar evolução metodológica
    2. **Foco em Complexidade**: Concentre-se nos 8.574 editais com múltiplas categorias (16,35%)
    3. **Análise de Divergências**: Use o checkbox para ver apenas casos onde CIC e STI divergem
    4. **Monitoramento de Mudanças**: Acompanhe o percentual de casos com predições diferentes entre as metodologias
    5. **Análise por Coordenadoria**: Monitore performance e volume por unidade organizacional
    6. **Observações Automáticas**: Campos em branco mostram "Classificação baseada em Termos Chave"
    7. **Impacto Financeiro**: Use filtros de valor para focar em editais de maior relevância
    8. **Qualidade da Base**: Aproveite que 83,65% têm classificação única (mais confiáveis)
    
    ### Para Analistas
    1. **Busca nos Termos-Chave**: Use a coluna "todos_termos" para entender critérios de classificação
    2. **Busca Múltipla**: Use ";" para buscar vários termos simultaneamente (ex: "educação; saúde; transporte")
    3. **Análise de Divergências**: Foque nos casos onde Predição CIC ≠ Predição STI para entender diferenças metodológicas
    4. **Comparação de Metodologias**: Analise sistematicamente as diferenças entre as abordagens CIC e STI
    5. **Análise de Observações**: Verifique observações específicas vs classificações automáticas
    6. **Análise de Coordenadorias**: Identifique unidades com mais editais ou maior valor
    7. **Validação do Modelo**: Foque nos 16,35% complexos para melhorar algoritmos
    8. **Baseline de Qualidade**: Use os 83,65% simples como referência de classificação correta
    9. **Dados Limpos**: Sistema remove automaticamente duplicatas para análises mais precisas
    
    ## ⚡ Funcionalidades Avançadas
    
    ### Performance e Atualização
    - Sistema otimizado para grandes volumes de dados
    - Cache inteligente com atualização automática
    - Dados sempre sincronizados com a planilha principal
    
    ### Dados Suportados
    - **Classificações Comparativas**: Nova vs Antiga classificação para análise evolutiva
    - **Observações Inteligentes**: Preenchimento automático para campos em branco
    - **Termos de Classificação**: Análise dos termos-chave utilizados na classificação
    - **Unidades Organizacionais**: Classificação por coordenadoria/estrutura do órgão
    - **Valores Estimados**: Análise financeira completa dos editais
    - **Dados Temporais**: Análise de tendências por ano
    - **Busca Avançada**: Pesquisa em múltiplas colunas com suporte a termos múltiplos
    
    ## 🔧 Solução de Problemas
    
    ### Problemas Comuns
    - **Dados não carregam**: Verifique sua conexão com a internet
    - **Dados desatualizados**: Clique em "Recarregar dados" ou espere a atualização automática
    - **Filtros sem resultado**: Verifique se os critérios não estão muito restritivos
    - **Gráficos em branco**: Alguns campos podem estar vazios nos dados
    
    ### Conexão com Google Sheets
    - Os dados são carregados diretamente da planilha oficial
    - Sistema detecta automaticamente mudanças na estrutura
    - Cache otimizado para performance e economia de recursos
    
    ### Suporte
    Para dúvidas técnicas ou sugestões de melhorias, entre em contato com a equipe de desenvolvimento.
    
    ---
    
    > 💼 **Projeto Predição de Editais - CIC2025 | TCERJ**  
    > **📊 Base completa:** 52.429 editais | R$ 244 bilhões | 729 unidades | 14+2 categorias  
    > Ferramenta de Consulta de Editais | Coordenadoria de Informações Estratégicas
    """)

def main():
    """Função principal da aplicação"""
    
    # Header principal
    st.markdown("""
    <div class="main-header">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1>📊 Projeto Predição de Editais - CIC2025</h1>
                <p style="color: #e2e8f0; margin: 0.5rem 0 0 0;">
                    Ferramenta de Consulta de Editais
                </p>
            </div>
            <div style="margin-left: 2rem;">
                <img src="https://tcerj365-my.sharepoint.com/:i:/g/personal/emanuellipc_tcerj_tc_br/EU_4T9vkz1BEmtF4qGFPdekB71dUQ1f_isaIoampssa5WQ?e=33qdcT" 
                     alt="CIC TCERJ Logo" 
                     style="height: 80px; width: auto; max-width: 150px; object-fit: contain;"
                     onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                <!-- Fallback caso a imagem não carregue -->
                <div style="width: 120px; height: 80px; background: rgba(255,255,255,0.1); border-radius: 8px; display: none; align-items: center; justify-content: center; color: white; font-size: 0.8rem;">
                    LOGO<br>CIC TCERJ
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Estatísticas gerais da base completa
    st.markdown("""
    <div class="alert-info">
        <h4>📈 Escopo da Base de Dados Completa</h4>
        <div style="display: flex; justify-content: space-around; text-align: center; margin: 1rem 0;">
            <div>
                <strong style="font-size: 1.5rem; color: #1e40af;">52.429</strong><br>
                <span style="color: #64748b;">Editais Analisados</span>
            </div>
            <div>
                <strong style="font-size: 1.5rem; color: #1e40af;">R$ 244 Bilhões</strong><br>
                <span style="color: #64748b;">Valor Total Estimado</span>
            </div>
            <div>
                <strong style="font-size: 1.5rem; color: #1e40af;">729</strong><br>
                <span style="color: #64748b;">Unidades Mapeadas</span>
            </div>
            <div>
                <strong style="font-size: 1.5rem; color: #1e40af;">14</strong><br>
                <span style="color: #64748b;">Categorias</span>
            </div>
            <div>
                <strong style="font-size: 1.5rem; color: #1e40af;">2</strong><br>
                <span style="color: #64748b;">Novas Categorias</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Opções de carregamento de dados
    st.markdown("### 📁 Fonte dos Dados")
    data_source = st.radio(
        "Escolha como carregar os dados:",
        ["🔗 SharePoint TCERJ (Automático)", "📄 Upload de Arquivo CSV"],
        horizontal=True
    )
    
    df = None
    error = None
    
    if data_source == "🔗 SharePoint TCERJ (Automático)":
        # Botão para forçar recarregamento dos dados
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("🔄 Recarregar Dados"):
                st.cache_data.clear()
                st.rerun()
        
        with col2:
            st.markdown("*Atualização automática a cada 5min*")
        
        # Diagnóstico da URL
        st.sidebar.markdown("### 🔗 Status da Conexão")
        st.sidebar.markdown(f"**URL da Planilha:** [Link TCERJ]({SHAREPOINT_URL})")
        
        # Carregamento dos dados do SharePoint
        with st.spinner("🔄 Carregando dados do SharePoint TCERJ..."):
            df, error = load_data_from_sharepoint()
    
    else:  # Upload de arquivo
        st.markdown("""
        <div class="alert-info">
            💡 <strong>Dica para arquivos com formatação problemática:</strong><br>
            • Abra o arquivo no Excel ou Google Sheets<br>
            • Faça uma limpeza dos dados (remover caracteres especiais)<br>
            • Salve como CSV (UTF-8) limpo<br>
            • Faça upload do arquivo limpo aqui
        </div>
        """, unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader(
            "📄 Selecione o arquivo CSV com os editais",
            type=['csv'],
            help="Arquivo CSV com encoding UTF-8 recomendado"
        )
        
        if uploaded_file is not None:
            with st.spinner("🔄 Processando arquivo..."):
                try:
                    # Primeira tentativa - encoding UTF-8
                    df = pd.read_csv(
                        uploaded_file,
                        encoding='utf-8',
                        on_bad_lines='skip',
                        engine='python',
                        dtype=str
                    )
                    
                    # Limpeza básica
                    df = df.dropna(how='all')
                    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
                    
                    st.success(f"✅ Arquivo carregado! {len(df)} linhas encontradas.")
                    
                except UnicodeDecodeError:
                    try:
                        # Segunda tentativa - encoding latin-1
                        uploaded_file.seek(0)
                        df = pd.read_csv(
                            uploaded_file,
                            encoding='latin-1',
                            on_bad_lines='skip',
                            engine='python',
                            dtype=str
                        )
                        df = df.dropna(how='all')
                        st.warning(f"⚠️ Arquivo carregado com encoding latin-1. {len(df)} linhas encontradas.")
                        
                    except Exception as e2:
                        error = f"Erro de encoding: {str(e2)}"
                        
                except Exception as e:
                    error = f"Erro ao processar arquivo: {str(e)}"
        
        else:
            st.info("👆 Selecione um arquivo CSV para começar a análise")
            return
    
    # Se houve erro, mostrar diagnóstico
    if error:
        st.error(f"❌ {error}")
        
        # Instruções específicas baseadas no tipo de erro
        if "conexão" in error.lower() or "timeout" in error.lower():
            st.markdown("""
            <div class="alert-warning">
                <h4>🌐 Problema de Conectividade</h4>
                <p><strong>Soluções alternativas:</strong></p>
                <ul>
                    <li>Mude para "📄 Upload de Arquivo CSV" acima</li>
                    <li>Baixe a planilha como CSV e faça upload manual</li>
                    <li>Verifique sua conexão com a internet</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
        elif "permission" in error.lower() or "403" in error.lower() or "autenticação" in error.lower():
            st.markdown("""
            <div class="alert-warning">
                <h4>🔒 Problema de Permissão do SharePoint TCERJ</h4>
                <p><strong>O SharePoint corporativo requer configurações especiais:</strong></p>
                <h5>Opção 1: Configurar Acesso Público (Recomendado)</h5>
                <ol>
                    <li>Abra a planilha no SharePoint</li>
                    <li>Clique em "Compartilhar" no canto superior direito</li>
                    <li>Clique em "Qualquer pessoa com o link pode visualizar"</li>
                    <li>Defina permissão como "Visualizar" apenas</li>
                    <li>Copie o novo link público gerado</li>
                    <li>Atualize o código com o novo link</li>
                </ol>
                <h5>Opção 2: Usar Upload Manual</h5>
                <ol>
                    <li>Baixe a planilha como Excel (.xlsx)</li>
                    <li>Abra no Excel e salve como CSV (UTF-8)</li>
                    <li>Use a opção "📄 Upload de Arquivo CSV" acima</li>
                </ol>
                <h5>Opção 3: Exportar para Serviço Público</h5>
                <ul>
                    <li>Exporte para Google Sheets público</li>
                    <li>Ou coloque o arquivo em repositório GitHub</li>
                    <li>Use um desses serviços no lugar do SharePoint corporativo</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
        else:
            st.markdown("""
            <div class="alert-warning">
                <h4>⚠️ Problema de Formatação dos Dados</h4>
                <p><strong>Soluções recomendadas:</strong></p>
                <ol>
                    <li><strong>Limpar dados no Google Sheets:</strong>
                        <ul>
                            <li>Abra a planilha original</li>
                            <li>Selecione todos os dados (Ctrl+A)</li>
                            <li>Copie para uma nova planilha</li>
                            <li>Use "Colar especial" → "Valores apenas"</li>
                            <li>Baixe como CSV e faça upload aqui</li>
                        </ul>
                    </li>
                    <li><strong>Usar Excel para limpeza:</strong>
                        <ul>
                            <li>Abra o arquivo no Excel</li>
                            <li>Use "Localizar e Substituir" para remover caracteres estranhos</li>
                            <li>Salve como CSV (UTF-8)</li>
                        </ul>
                    </li>
                    <li><strong>Hospedagem alternativa:</strong>
                        <ul>
                            <li>Coloque o CSV limpo no GitHub</li>
                            <li>Use a URL raw no código</li>
                        </ul>
                    </li>
                </ol>
            </div>
            """, unsafe_allow_html=True)
        
        return
    
    # Se os dados foram carregados com sucesso
    if df is not None and len(df) > 0:
        st.markdown(f"""
        <div class="alert-success">
            ✅ <strong>Dados carregados com sucesso!</strong><br>
            📋 52.429 editais encontrados | 8.574 editais em mais de uma categoria (16,35%) | 43.855 editais em apenas uma categoria (83,65%) | 🕐 {datetime.now().strftime('%H:%M:%S')}
        </div>
        """, unsafe_allow_html=True)
        
        # Conversões de tipos mais seguras
        if 'data realizacao licitacao' in df.columns:
            df['data realizacao licitacao'] = pd.to_datetime(df['data realizacao licitacao'], errors='coerce')
        
        if 'ano' in df.columns:
            df['ano'] = pd.to_numeric(df['ano'], errors='coerce')
        
        if 'valor estimado' in df.columns:
            # Limpeza de valores monetários
            df['valor estimado'] = df['valor estimado'].astype(str).str.replace(r'[^\d.,]', '', regex=True)
            df['valor estimado'] = df['valor estimado'].str.replace(',', '.', regex=False)
            df['valor estimado'] = pd.to_numeric(df['valor estimado'], errors='coerce')
        
        if 'pontuacao' in df.columns:
            df['pontuacao'] = df['pontuacao'].astype(str).str.replace(',', '.', regex=False)
            df['pontuacao'] = pd.to_numeric(df['pontuacao'], errors='coerce')
            
        if 'pontuacao_final' in df.columns:
            df['pontuacao_final'] = df['pontuacao_final'].astype(str).str.replace(',', '.', regex=False)
            df['pontuacao_final'] = pd.to_numeric(df['pontuacao_final'], errors='coerce')
        
        # Processamento da coluna observacoes - preenche valores em branco
        if 'observacoes' in df.columns:
            df['observacoes'] = df['observacoes'].apply(
                lambda x: x if pd.notna(x) and str(x).strip() != '' else 'Classificação baseada em Termos Chave'
            )
        
        # Renomeação de colunas específicas
        column_renames = {
            'classificacao_final - Copiar': 'Predição CIC',
            'predicao classificacao': 'Predição STI'
        }
        
        for old_name, new_name in column_renames.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # Remoção de duplicatas ignorando a coluna 'classificacao_final'
        columns_for_dedup = [col for col in df.columns if col != 'classificacao_final']
        if columns_for_dedup:
            df = df.drop_duplicates(subset=columns_for_dedup, keep='first')
        
        # Informações dos dados na sidebar
        st.sidebar.markdown("### 📊 Informações dos Dados")
        
        # Status da conexão com ícone verde
        if data_source == "🔗 SharePoint TCERJ (Automático)":
            st.sidebar.markdown("**Fonte:** 🔗 SharePoint TCERJ (Automático) 🟢")
        else:
            st.sidebar.markdown("**Fonte:** 📄 Upload Manual 🔵")
        
        # Informações estatísticas fixas da base completa
        st.sidebar.markdown("**Total de Editais:** 52.429")
        st.sidebar.markdown("**Total de Categorias:** 14") 
        st.sidebar.markdown("**Total Estimado:** R$ 244 bilhões")
        
        # **CRIAÇÃO DOS FILTROS**
        st.sidebar.markdown("### 🔍 Filtros de Pesquisa")
        
        # Filtro por texto livre
        search_term = st.sidebar.text_input(
            "🔎 Buscar por termo (objeto, ente, etc.)",
            placeholder="Digite aqui para buscar... (use ; para múltiplos termos)"
        )
        
        # Filtros específicos
        filters = {}
        
        # Nova Classificação (antes Classificação Final) - PRIMEIRO
        if 'classificacao_final' in df.columns:
            classificacoes = ['Todas'] + sorted(df['classificacao_final'].dropna().unique().tolist())
            filters['classificacao_final'] = st.sidebar.selectbox(
                "📂 Nova Classificação",
                classificacoes
            )
        
        # Predição CIC
        if 'Predição CIC' in df.columns:
            predicoes_cic = ['Todas'] + sorted(df['Predição CIC'].dropna().unique().tolist())
            filters['Predição CIC'] = st.sidebar.selectbox(
                "🔮 Predição CIC",
                predicoes_cic
            )
        
        # Predição STI
        if 'Predição STI' in df.columns:
            predicoes_sti = ['Todas'] + sorted(df['Predição STI'].dropna().unique().tolist())
            filters['Predição STI'] = st.sidebar.selectbox(
                "🔄 Predição STI",
                predicoes_sti
            )
        
        if 'unidade' in df.columns:
            unidades = ['Todas'] + sorted(df['unidade'].dropna().unique().tolist())
            filters['unidade'] = st.sidebar.selectbox(
                "🏢 Unidade",
                unidades
            )
        
        if 'ente' in df.columns:
            entes = ['Todos'] + sorted(df['ente'].dropna().unique().tolist())
            filters['ente'] = st.sidebar.selectbox(
                "🏛️ Ente",
                entes
            )
        
        if 'modalidade' in df.columns:
            modalidades = ['Todas'] + sorted(df['modalidade'].dropna().unique().tolist())
            filters['modalidade'] = st.sidebar.selectbox(
                "📋 Modalidade",
                modalidades
            )
        
        if 'ano' in df.columns:
            anos_disponiveis = sorted(df['ano'].dropna().unique().tolist())
            if anos_disponiveis:
                filters['ano'] = st.sidebar.selectbox(
                    "📅 Ano",
                    ['Todos'] + [str(int(ano)) for ano in anos_disponiveis]
                )
        
        # Filtro por valor
        if 'valor estimado' in df.columns:
            valor_min = float(df['valor estimado'].min()) if not df['valor estimado'].isna().all() else 0
            valor_max = float(df['valor estimado'].max()) if not df['valor estimado'].isna().all() else 1000000
            
            if valor_max > valor_min:
                valor_range = st.sidebar.slider(
                    "💰 Faixa de Valor Estimado (R$)",
                    min_value=valor_min,
                    max_value=valor_max,
                    value=(valor_min, valor_max),
                    format="R$ %.0f"
                )
                filters['valor_range'] = valor_range
        
        # Aplicação dos filtros
        filtered_df = apply_filters(df, search_term, filters)
        
        # Criação das abas após o processamento dos filtros
        tab1, tab2, tab3 = st.tabs(["📊 Análise de Dados", "📈 Dashboard", "📚 Ajuda"])
        
        with tab1:
            # Métricas de visão geral
            st.markdown("### 📊 Dados Carregados para Análise")
            create_overview_metrics(filtered_df)
            
            # Informações adicionais sobre categorização
            st.markdown("### 📈 Análise de Categorização")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    label="📋 Editais em Múltiplas Categorias",
                    value="8.574",
                    delta="16,35%"
                )
            
            with col2:
                st.metric(
                    label="📄 Editais em Categoria Única",
                    value="43.855", 
                    delta="83,65%"
                )
            
            with col3:
                # Calcula % de mudança entre as predições
                if 'Predição CIC' in filtered_df.columns and 'Predição STI' in filtered_df.columns:
                    total_linhas = len(filtered_df)
                    if total_linhas > 0:
                        linhas_diferentes = len(filtered_df[filtered_df['Predição CIC'] != filtered_df['Predição STI']])
                        percentual_mudanca = (linhas_diferentes / total_linhas) * 100
                        
                        st.metric(
                            label="🔄 Mudanças nas Predições",
                            value=f"{percentual_mudanca:.1f}%",
                            delta=f"{linhas_diferentes:,} casos"
                        )
                    else:
                        st.metric(
                            label="🔄 Mudanças nas Predições",
                            value="0%",
                            delta="0 casos"
                        )
            
            # Texto explicativo sobre as mudanças
            if 'Predição CIC' in filtered_df.columns and 'Predição STI' in filtered_df.columns:
                total_linhas = len(filtered_df)
                if total_linhas > 0:
                    linhas_diferentes = len(filtered_df[filtered_df['Predição CIC'] != filtered_df['Predição STI']])
                    percentual_mudanca = (linhas_diferentes / total_linhas) * 100
                    
                    st.info(f"📊 **Foram identificadas mudanças em {percentual_mudanca:.1f}% dos casos, onde a predição CIC difere da predição STI.**")
            
            if len(filtered_df) == 0:
                st.warning("⚠️ Nenhum resultado encontrado com os filtros aplicados. Tente ajustar os critérios de busca.")
            else:
                # Exibir informações dos filtros aplicados
                if search_term or any(v not in ['Todas', 'Todos'] for v in filters.values() if isinstance(v, str)):
                    filter_info = f"🔍 **Filtros aplicados** - Exibindo {len(filtered_df):,} de 52.429 editais"
                    
                    # Adiciona informação sobre busca múltipla se aplicável
                    if search_term and ';' in search_term:
                        terms_count = len([term.strip() for term in search_term.split(';') if term.strip()])
                        filter_info += f" | 🔎 Busca múltipla: {terms_count} termos"
                    
                    st.info(filter_info)
                
                # Tabela de dados
                display_data_table(filtered_df)
        
        with tab2:
            st.markdown("### 📊 Dashboard Analítico")
            
            if len(filtered_df) > 0:
                # Mostrar informação de filtros se aplicados
                if search_term or any(v not in ['Todas', 'Todos'] for v in filters.values() if isinstance(v, str)):
                    filter_info = f"🔍 **Visualizando dados filtrados** - {len(filtered_df):,} de 52.429 editais"
                    
                    # Adiciona informação sobre busca múltipla se aplicável
                    if search_term and ';' in search_term:
                        terms_count = len([term.strip() for term in search_term.split(';') if term.strip()])
                        filter_info += f" | 🔎 Busca múltipla: {terms_count} termos"
                    
                    st.info(filter_info)
                
                # Métricas principais
                st.markdown("### 📊 Dados Filtrados para Análise")
                create_overview_metrics(filtered_df)
                
                # Informações adicionais sobre categorização
                st.markdown("### 📈 Análise de Categorização")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        label="📋 Editais em Múltiplas Categorias",
                        value="8.574",
                        delta="16,35%"
                    )
                
                with col2:
                    st.metric(
                        label="📄 Editais em Categoria Única",
                        value="43.855", 
                        delta="83,65%"
                    )
                
                with col3:
                    # Calcula % de mudança entre as predições
                    if 'Predição CIC' in filtered_df.columns and 'Predição STI' in filtered_df.columns:
                        total_linhas = len(filtered_df)
                        if total_linhas > 0:
                            linhas_diferentes = len(filtered_df[filtered_df['Predição CIC'] != filtered_df['Predição STI']])
                            percentual_mudanca = (linhas_diferentes / total_linhas) * 100
                            
                            st.metric(
                                label="🔄 Mudanças nas Predições",
                                value=f"{percentual_mudanca:.1f}%",
                                delta=f"{linhas_diferentes:,} casos"
                            )
                        else:
                            st.metric(
                                label="🔄 Mudanças nas Predições",
                                value="0%",
                                delta="0 casos"
                            )
                
                # Texto explicativo sobre as mudanças
                if 'Predição CIC' in filtered_df.columns and 'Predição STI' in filtered_df.columns:
                    total_linhas = len(filtered_df)
                    if total_linhas > 0:
                        linhas_diferentes = len(filtered_df[filtered_df['Predição CIC'] != filtered_df['Predição STI']])
                        percentual_mudanca = (linhas_diferentes / total_linhas) * 100
                        
                        st.info(f"📊 **Foram identificadas mudanças em {percentual_mudanca:.1f}% dos casos, onde a predição CIC difere da predição STI.**")
                
                # Gráficos
                create_charts(filtered_df)
                
                # Estatísticas adicionais
                if 'classificacao_final' in filtered_df.columns:
                    st.markdown("### 📋 Análise Detalhada por Classificação")
                    
                    classification_stats = filtered_df.groupby('classificacao_final').agg({
                        'valor estimado': ['count', 'sum', 'mean'],
                        'pontuacao': 'mean' if 'pontuacao' in filtered_df.columns else 'count'
                    }).round(2)
                    
                    classification_stats.columns = ['Quantidade', 'Valor Total', 'Valor Médio', 'Pontuação Média']
                    
                    st.dataframe(
                        classification_stats.sort_values('Quantidade', ascending=False),
                        use_container_width=True
                    )
            else:
                st.warning("⚠️ Nenhum dado disponível para exibir no dashboard com os filtros aplicados.")
        
        with tab3:
            show_help_tab()
    
    else:
        st.markdown("""
        <div class="alert-info">
            <h3>👋 Bem-vindo ao Projeto Predição de Editais - CIC2025!</h3>
            <p><strong>📊 Nossa base completa contém:</strong></p>
            <ul style="margin: 1rem 0;">
                <li><strong>52.429 editais</strong> analisados e classificados</li>
                <li><strong>R$ 244 bilhões</strong> em valor total estimado</li>
                <li><strong>729 unidades</strong> organizacionais mapeadas</li>
                <li><strong>14 categorias</strong> originais + <strong>2 novas categorias</strong></li>
            </ul>
            
            <p><strong>🚀 Para começar sua consulta:</strong></p>
            <ol>
                <li>📁 Selecione uma fonte de dados acima</li>
                <li>🔍 Use os filtros para encontrar informações específicas</li>
                <li>📊 Explore as visualizações no dashboard</li>
                <li>📥 Exporte os dados filtrados quando necessário</li>
            </ol>
            
            <p><strong>💡 Dica:</strong> Acesse a aba "📚 Ajuda" para instruções detalhadas sobre todas as funcionalidades!</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()