import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx
import time
import os
import sys
import importlib.util
from pathlib import Path

# Set up page configurations
st.set_page_config(
    page_title="SET50 Major Shareholders Dashboard", page_icon="📋", layout="wide"
)

# ----------------------------------------------------
# 1. DYNAMICALLY LOAD THE BACKEND HELPER MODULE
# ----------------------------------------------------
db_module_path = Path(__file__).parent / "1_HW01" / "shareholder_db.py"
if db_module_path.exists():
    spec = importlib.util.spec_from_file_location("shareholder_db", db_module_path)
    shareholder_db = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shareholder_db)
else:
    st.error("Backend helper module `shareholder_db.py` not found in pages/1_HW01/")
    st.stop()

# Extract utility functions and constants from the module
SET50_SYMBOLS = shareholder_db.SET50_SYMBOLS
fetch_all_shareholders = shareholder_db.fetch_all_shareholders
save_shareholders = shareholder_db.save_shareholders
get_scraper_session = shareholder_db.get_scraper_session
scrape_symbol_shareholders = shareholder_db.scrape_symbol_shareholders

# ----------------------------------------------------
# 2. CUSTOM CSS STYLING
# ----------------------------------------------------
st.markdown(
    """
<style>
    .reportview-container {
        background: #f8f9fa;
    }
    .main-header {
        font-family: 'Outfit', 'Inter', sans-serif;
        color: #1E3A8A;
        font-weight: 700;
        margin-bottom: 0px;
    }
    .sub-header {
        color: #4B5563;
        margin-bottom: 25px;
    }
    .metric-card {
        background-color: white;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border: 1px solid #E5E7EB;
        text-align: center;
    }
    .metric-value {
        font-size: 24px;
        font-weight: 700;
        color: #2563EB;
    }
    .metric-label {
        font-size: 14px;
        color: #6B7280;
        margin-top: 5px;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        background-color: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .insight-card {
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 15px;
        box-shadow: 0 1px 3px 0 rgba(0,0,0,0.05);
        border: 1px solid #E5E7EB;
        border-left: 5px solid;
    }
    .insight-card.investor {
        background-color: #FEF2F2;
        border-left-color: #EF4444;
        border-top-color: #FEE2E2;
        border-right-color: #FEE2E2;
        border-bottom-color: #FEE2E2;
    }
    .insight-card.stock {
        background-color: #EFF6FF;
        border-left-color: #3B82F6;
        border-top-color: #DBEAFE;
        border-right-color: #DBEAFE;
        border-bottom-color: #DBEAFE;
    }
    .insight-title {
        font-family: 'Outfit', 'Inter', sans-serif;
        font-size: 15px;
        font-weight: 700;
        margin-bottom: 6px;
    }
    .insight-card.investor .insight-title {
        color: #991B1B;
    }
    .insight-card.stock .insight-title {
        color: #1E40AF;
    }
    .insight-entity {
        font-family: 'Inter', sans-serif;
        font-size: 14px;
        font-weight: 600;
        color: #1F2937;
        background: rgba(255, 255, 255, 0.75);
        padding: 4px 8px;
        border-radius: 4px;
        display: inline-block;
        margin-bottom: 8px;
        border: 1px dashed rgba(0, 0, 0, 0.08);
    }
    .insight-desc {
        font-family: 'Inter', sans-serif;
        font-size: 13px;
        color: #4B5563;
        line-height: 1.5;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ----------------------------------------------------
# 3. TITLE AND HEADER
# ----------------------------------------------------
st.markdown(
    "<h1 class='main-header'>📋 ข้อมูลผู้ถือหุ้นรายใหญ่ SET50</h1>", unsafe_allow_html=True
)
st.markdown(
    "<p class='sub-header'>Scrape, monitor, and analyze major shareholders of the top 50 listed companies on the Stock Exchange of Thailand.</p>",
    unsafe_allow_html=True,
)

# ----------------------------------------------------
# 4. SIDEBAR SETUP
# ----------------------------------------------------
st.sidebar.image(
    "https://media.set.or.th/common/set/thumbnail/stock-major-shareholder.jpg",
    use_column_width=True,
)
st.sidebar.title("Settings & Control")

st.sidebar.info(
    "📂 Data is stored locally in `set50_shareholders.json` inside the `pages/1_HW01` folder."
)

# ----------------------------------------------------
# 5. SCRAPER FUNCTIONALITY TRIGGER
# ----------------------------------------------------
if st.sidebar.button("🔄 Refresh Shareholders Data", use_container_width=True):
    st.subheader("Scraping Progress & Logs")
    progress_bar = st.progress(0.0)

    # Using Streamlit's status widget for clean collapsible log reporting
    with st.status("Initializing Scraper Session...", expanded=True) as status_box:
        try:
            st.write("Establishing connection to SET website...")
            session = get_scraper_session()
            st.write(
                "Session established. Scraping top 5 shareholders for 50 companies..."
            )

            success_count = 0
            error_symbols = []

            for idx, sym in enumerate(SET50_SYMBOLS):
                progress_val = (idx + 1) / len(SET50_SYMBOLS)
                progress_bar.progress(progress_val)

                st.write(f"Scraping `{sym}` ({idx + 1}/50)...")

                try:
                    sh_list, book_close = scrape_symbol_shareholders(session, sym)
                    if sh_list:
                        # Save directly to local JSON file
                        save_shareholders(sym, sh_list, book_close)
                        success_count += 1
                    else:
                        st.write(f"⚠️ `{sym}` returned empty shareholder list.")
                        error_symbols.append(sym)
                except Exception as sym_err:
                    st.write(f"❌ Error scraping `{sym}`: {sym_err}")
                    error_symbols.append(sym)

                # Polite rate limiting to avoid getting blocked
                time.sleep(0.3)

            if success_count == len(SET50_SYMBOLS):
                status_box.update(
                    label="Scraping Completed Successfully!",
                    state="complete",
                    expanded=False,
                )
                st.success(
                    f"Successfully scraped and saved shareholder data for all {success_count} SET50 symbols!"
                )
            else:
                status_box.update(
                    label=f"Scraping Completed with Warnings ({success_count}/{len(SET50_SYMBOLS)} successful)",
                    state="complete",
                    expanded=True,
                )
                st.warning(
                    f"Completed with errors. Saved: {success_count} symbols. Failed symbols: {', '.join(error_symbols)}"
                )

            # Force reload of data
            if "db_data" in st.session_state:
                del st.session_state["db_data"]
            st.rerun()

        except Exception as scraper_err:
            status_box.update(label="Scraping Failed!", state="error", expanded=True)
            st.error(f"A general scraping error occurred: {scraper_err}")

# ----------------------------------------------------
# 6. LOAD DATA FROM JSON FILE
# ----------------------------------------------------
db_records = []
# Cache data in Streamlit session state to avoid constant disk read on render
if "db_data" not in st.session_state:
    st.session_state["db_data"] = fetch_all_shareholders()
db_records = st.session_state["db_data"]

# ----------------------------------------------------
# 7. MAIN DASHBOARD CONTENT
# ----------------------------------------------------
if not db_records:
    st.info(
        "💡 **No shareholder records found.** Please click the **Refresh Shareholders Data** button in the sidebar to scrape the data from the SET portal."
    )
else:
    # Convert records list to Pandas DataFrame
    df = pd.DataFrame(db_records)

    # Format updated_at nicely
    if "updated_at" in df.columns:
        df["updated_at"] = pd.to_datetime(df["updated_at"])

    # Establish UI Tabs
    tab_net, tab_explorer, tab_search, tab_analytics = st.tabs(
        [
            "🕸️ Network Analysis",
            "🔍 Ticker Explorer",
            "🕸️ Shareholder Network Search",
            "📊 Market Analytics & Insights",
        ]
    )

    # TAB 1: TICKER EXPLORER
    with tab_explorer:
        st.subheader("Explore Shareholders by Ticker")
        selected_ticker = st.selectbox("Select a Stock Symbol:", SET50_SYMBOLS)

        # Filter data for selected ticker
        ticker_df = df[df["symbol"] == selected_ticker].sort_values(by="sequence")

        if ticker_df.empty:
            st.warning(
                f"No data saved for ticker `{selected_ticker}` yet. Please refresh the data."
            )
        else:
            # Display stats cards
            book_date = ticker_df.iloc[0]["book_close_date"]
            last_up = (
                ticker_df.iloc[0]["updated_at"].strftime("%Y-%m-%d %H:%M:%S")
                if "updated_at" in ticker_df.columns
                else "N/A"
            )
            total_shares_represented = ticker_df["shares"].sum()
            total_percent_represented = ticker_df["percent"].sum()

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(
                    f"<div class='metric-card'><div class='metric-value'>{book_date}</div><div class='metric-label'>Book Close Date</div></div>",
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    f"<div class='metric-card'><div class='metric-value'>{total_shares_represented:,.0f}</div><div class='metric-label'>Top 5 Shares Combined</div></div>",
                    unsafe_allow_html=True,
                )
            with c3:
                st.markdown(
                    f"<div class='metric-card'><div class='metric-value'>{total_percent_represented:.2f}%</div><div class='metric-label'>Top 5 Holding Percent</div></div>",
                    unsafe_allow_html=True,
                )
            with c4:
                st.markdown(
                    f"<div class='metric-card'><div class='metric-value'>{last_up}</div><div class='metric-label'>Last Scraped</div></div>",
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)

            # Format and show table
            display_df = ticker_df[["sequence", "name", "shares", "percent"]].copy()
            display_df.columns = [
                "Rank (ลำดับ)",
                "Shareholder (ผู้ถือหุ้นรายใหญ่)",
                "Shares (จำนวนหุ้น)",
                "Holding % (% หุ้น)",
            ]

            # Format shares column with commas
            display_df["Shares (จำนวนหุ้น)"] = display_df["Shares (จำนวนหุ้น)"].apply(
                lambda x: f"{x:,.0f}" if pd.notnull(x) else "-"
            )
            display_df["Holding % (% หุ้น)"] = display_df["Holding % (% หุ้น)"].apply(
                lambda x: f"{x:.2f}%" if pd.notnull(x) else "-"
            )

            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # Plotly pie chart of top 5 shareholders
            fig_pie = px.pie(
                ticker_df,
                values="percent",
                names="name",
                title=f"Share Distribution of Top 5 Shareholders in {selected_ticker}",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig_pie.update_layout(margin=dict(t=50, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)

    # TAB 2: SHAREHOLDER NETWORK SEARCH
    with tab_search:
        st.subheader("Search Shareholder Holdings Network")
        st.markdown(
            "Query a major shareholder name (e.g. `ไทยเอ็นวีดีอาร์` or `กระทรวงการคลัง` or `วายุภักษ์`) to discover all their major holdings across the SET50 index."
        )

        search_query = st.text_input(
            "Enter Shareholder Name (Supports Partial Matches):",
            placeholder="e.g. ไทยเอ็นวีดีอาร์",
        )

        if search_query:
            # Perform case-insensitive search
            matches_df = df[
                df["name"].str.contains(search_query, case=False, na=False)
            ].copy()

            if matches_df.empty:
                st.info(f"No holdings found matching '{search_query}'.")
            else:
                st.success(
                    f"Found {len(matches_df)} holding(s) matching '{search_query}'."
                )

                # Format table
                results_df = matches_df[
                    [
                        "symbol",
                        "sequence",
                        "name",
                        "shares",
                        "percent",
                        "book_close_date",
                    ]
                ].copy()
                results_df.columns = [
                    "Stock",
                    "Rank (ลำดับ)",
                    "Shareholder Name",
                    "Shares",
                    "Holding %",
                    "Book Close Date",
                ]
                results_df = results_df.sort_values(by="Holding %", ascending=False)

                # Format numbers
                results_df["Shares"] = results_df["Shares"].apply(lambda x: f"{x:,.0f}")
                results_df["Holding %"] = results_df["Holding %"].apply(
                    lambda x: f"{x:.2f}%"
                )

                st.dataframe(results_df, use_container_width=True, hide_index=True)

                # Bar chart of matching holdings
                fig_match_bar = px.bar(
                    matches_df,
                    x="symbol",
                    y="percent",
                    color="percent",
                    title=f"Holding Percentages by '{search_query}' across SET50",
                    labels={"symbol": "Stock Symbol", "percent": "Holding %"},
                    color_continuous_scale=px.colors.sequential.Viridis,
                )
                st.plotly_chart(fig_match_bar, use_container_width=True)

    # TAB 3: MARKET ANALYTICS
    with tab_analytics:
        st.subheader("SET50 Shareholder Analytics")

        # Calculate shareholder frequencies
        freq_df = df["name"].value_counts().reset_index()
        freq_df.columns = ["Shareholder Name", "Count in SET50 Top 5"]

        col_an1, col_an2 = st.columns([2, 1])

        with col_an1:
            st.markdown("#### Top 10 Most Common Shareholders in SET50 Companies")
            top_10_freq = freq_df.head(10)

            fig_freq_bar = px.bar(
                top_10_freq,
                x="Count in SET50 Top 5",
                y="Shareholder Name",
                orientation="h",
                color="Count in SET50 Top 5",
                color_continuous_scale=px.colors.sequential.Plasma,
                text_auto=True,
                title="Number of SET50 Companies where Shareholder is in Top 5",
            )
            # Order bar chart from highest to lowest
            fig_freq_bar.update_layout(
                yaxis={"categoryorder": "total ascending"}, showlegend=False
            )
            st.plotly_chart(fig_freq_bar, use_container_width=True)

        with col_an2:
            st.markdown("#### Frequency Table")
            st.dataframe(freq_df.head(15), use_container_width=True, hide_index=True)

        st.markdown("<hr>", unsafe_allow_html=True)

        # Additional Insights: Largest holdings by percent
        st.markdown("#### Largest Individual Holdings in the SET50 Index")
        largest_holdings = df.sort_values(by="percent", ascending=False).head(10)

        large_display = largest_holdings[
            ["symbol", "name", "shares", "percent", "sequence"]
        ].copy()
        large_display.columns = [
            "Stock",
            "Shareholder Name",
            "Shares",
            "Holding %",
            "Rank",
        ]
        large_display["Shares"] = large_display["Shares"].apply(lambda x: f"{x:,.0f}")
        large_display["Holding %"] = large_display["Holding %"].apply(
            lambda x: f"{x:.2f}%"
        )

        st.dataframe(large_display, use_container_width=True, hide_index=True)

    # TAB 4: NETWORK ANALYSIS
    with tab_net:
        st.subheader("🕸️ Shareholder-Stock Network Analysis (SNA)")
        st.markdown(
            "Using **NetworkX**, we model the relationships between SET50 stocks and their major shareholders. "
            "We analyze this as a **Bipartite Network** (where edges connect shareholders to stocks) and also "
            "project it into a **One-Mode Stock-Stock Network** (connecting stocks that share common top investors)."
        )

        # Build networkx graph
        G = nx.Graph()
        stocks = df["symbol"].unique()

        for _, row in df.iterrows():
            sh_name = row["name"]
            symbol = row["symbol"]
            percent = float(row.get("percent", 0))

            G.add_node(sh_name, type="shareholder")
            G.add_node(symbol, type="stock")
            G.add_edge(sh_name, symbol, weight=percent)

        # Compute Bipartite Projections
        from networkx.algorithms import bipartite

        stocks_set = {n for n, d in G.nodes(data=True) if d["type"] == "stock"}
        G_stock = bipartite.projected_graph(G, stocks_set)

        # Network statistics
        num_nodes = G.number_of_nodes()
        num_edges = G.number_of_edges()
        density = nx.density(G)

        # Bipartite degree calculation: Degree of shareholders
        degrees = dict(G.degree())
        sh_degrees = {
            node: deg
            for node, deg in degrees.items()
            if G.nodes[node]["type"] == "shareholder"
        }
        avg_sh_degree = sum(sh_degrees.values()) / len(sh_degrees) if sh_degrees else 0

        # Connected Components
        components = list(nx.connected_components(G))
        num_components = len(components)
        largest_comp_size = len(max(components, key=len)) if components else 0

        # Stock-Stock projected metrics
        stock_density = nx.density(G_stock)
        stock_transitivity = nx.transitivity(G_stock)

        # Metric Cards Layout - Row 1
        c_net1, c_net2, c_net3, c_net4 = st.columns(4)
        with c_net1:
            st.markdown(
                f"<div class='metric-card'><div class='metric-value'>{num_nodes}</div><div class='metric-label'>Total Nodes (Stocks & Investors)</div></div>",
                unsafe_allow_html=True,
            )
        with c_net2:
            st.markdown(
                f"<div class='metric-card'><div class='metric-value'>{num_edges}</div><div class='metric-label'>Total Edges (Holdings)</div></div>",
                unsafe_allow_html=True,
            )
        with c_net3:
            st.markdown(
                f"<div class='metric-card'><div class='metric-value'>{num_components}</div><div class='metric-label'>Connected Components</div></div>",
                unsafe_allow_html=True,
            )
        with c_net4:
            st.markdown(
                f"<div class='metric-card'><div class='metric-value'>{largest_comp_size}</div><div class='metric-label'>Largest Component Size</div></div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

        # Metric Cards Layout - Row 2
        c_net5, c_net6, c_net7, c_net8 = st.columns(4)
        with c_net5:
            st.markdown(
                f"<div class='metric-card'><div class='metric-value'>{density:.4f}</div><div class='metric-label'>Bipartite Density</div></div>",
                unsafe_allow_html=True,
            )
        with c_net6:
            st.markdown(
                f"<div class='metric-card'><div class='metric-value'>{avg_sh_degree:.2f}</div><div class='metric-label'>Avg Stocks Per Investor</div></div>",
                unsafe_allow_html=True,
            )
        with c_net7:
            st.markdown(
                f"<div class='metric-card'><div class='metric-value'>{stock_density:.4f}</div><div class='metric-label'>Stock-Stock Proj. Density</div></div>",
                unsafe_allow_html=True,
            )
        with c_net8:
            st.markdown(
                f"<div class='metric-card'><div class='metric-value'>{stock_transitivity:.4f}</div><div class='metric-label'>Stock-Stock Transitivity</div></div>",
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # ----------------------------------------------------
        # DYNAMIC KEY NETWORK ROLE INSIGHTS
        # ----------------------------------------------------
        # Compute centralities
        deg_cent = nx.degree_centrality(G)
        between_cent = nx.betweenness_centrality(G)
        try:
            eigen_cent = nx.eigenvector_centrality(G, max_iter=2000)
        except Exception:
            eigen_cent = {}

        # Helper to separate stock/shareholder
        def get_top_nodes_by_metric(metric_dict, node_type, limit=1):
            nodes = [n for n in metric_dict if G.nodes[n]["type"] == node_type]
            sorted_nodes = sorted(nodes, key=lambda x: metric_dict[x], reverse=True)
            return sorted_nodes[:limit]

        top_sh_deg = get_top_nodes_by_metric(deg_cent, "shareholder", 3)
        top_stock_deg = get_top_nodes_by_metric(deg_cent, "stock", 3)
        top_between_sh = get_top_nodes_by_metric(between_cent, "shareholder", 3)
        top_between_stock = get_top_nodes_by_metric(between_cent, "stock", 3)
        top_eigen_sh = (
            get_top_nodes_by_metric(eigen_cent, "shareholder", 3) if eigen_cent else []
        )
        top_eigen_stock = (
            get_top_nodes_by_metric(eigen_cent, "stock", 3) if eigen_cent else []
        )

        # Helper to format top 3 ranked nodes into HTML
        def format_top_3_html(nodes_list, detail_fn):
            html_lines = []
            medals = ["🥇", "🥈", "🥉"]
            for rank, node in enumerate(nodes_list[:3]):
                detail = detail_fn(node)
                html_lines.append(
                    f"<div style='margin-bottom: 6px; font-size: 14px; font-family: \"Inter\", sans-serif;'>"
                    f"{medals[rank]} <strong>{node}</strong> {detail}</div>"
                )
            return "".join(html_lines)

        with st.expander(
            "💡 View Dynamic Network Role & Investment Insights", expanded=True
        ):
            col_ins1, col_ins2 = st.columns(2)
            with col_ins1:
                st.markdown("#### 🔴 Key Investor Insights")
                if top_sh_deg:
                    st.markdown(
                        f"""
                        <div class="insight-card investor">
                            <div class="insight-title">👑 Most Diversified Investors (Top 3)</div>
                            <div class="insight-desc">
                                {format_top_3_html(top_sh_deg, lambda n: f"(holds <strong>{G.degree(n)}</strong> stocks)")}
                                <div style="margin-top: 8px; font-size: 12px; font-style: italic; color: #7f1d1d;">
                                    These investors hold major stakes in the highest number of unique companies.
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                if top_between_sh:
                    st.markdown(
                        f"""
                        <div class="insight-card investor">
                            <div class="insight-title">🌉 Key Connector / Bridge Investors (Top 3)</div>
                            <div class="insight-desc">
                                {format_top_3_html(top_between_sh, lambda n: f"(betweenness: <strong>{between_cent[n]:.4f}</strong>)")}
                                <div style="margin-top: 8px; font-size: 12px; font-style: italic; color: #7f1d1d;">
                                    These investors act as critical pipelines connecting otherwise separate portfolios.
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                if top_eigen_sh:
                    st.markdown(
                        f"""
                        <div class="insight-card investor">
                            <div class="insight-title">⭐ Most Influential Investors (Top 3)</div>
                            <div class="insight-desc">
                                {format_top_3_html(top_eigen_sh, lambda n: f"(influence: <strong>{eigen_cent[n]:.4f}</strong>)")}
                                <div style="margin-top: 8px; font-size: 12px; font-style: italic; color: #7f1d1d;">
                                    These investors hold stakes in other highly central, influential market entities.
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            with col_ins2:
                st.markdown("#### 🔵 Key Stock Insights")
                if top_stock_deg:
                    st.markdown(
                        f"""
                        <div class="insight-card stock">
                            <div class="insight-title">👥 Most Shared Ownership Stocks (Top 3)</div>
                            <div class="insight-desc">
                                {format_top_3_html(top_stock_deg, lambda n: f"(has <strong>{G.degree(n)}</strong> major owners)")}
                                <div style="margin-top: 8px; font-size: 12px; font-style: italic; color: #1e3a8a;">
                                    These companies exhibit the highest concentration of shared institutional co-investors.
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                if top_between_stock:
                    st.markdown(
                        f"""
                        <div class="insight-card stock">
                            <div class="insight-title">🌉 Strategic Bridge Stocks (Top 3)</div>
                            <div class="insight-desc">
                                {format_top_3_html(top_between_stock, lambda n: f"(betweenness: <strong>{between_cent[n]:.4f}</strong>)")}
                                <div style="margin-top: 8px; font-size: 12px; font-style: italic; color: #1e3a8a;">
                                    These stocks sit at the intersection of diverse investor portfolios across sectors.
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                if top_eigen_stock:
                    st.markdown(
                        f"""
                        <div class="insight-card stock">
                            <div class="insight-title">⭐ Core Index Backbone Stocks (Top 3)</div>
                            <div class="insight-desc">
                                {format_top_3_html(top_eigen_stock, lambda n: f"(influence: <strong>{eigen_cent[n]:.4f}</strong>)")}
                                <div style="margin-top: 8px; font-size: 12px; font-style: italic; color: #1e3a8a;">
                                    These companies are heavily co-owned by highly central, high-wealth institutional groups.
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        st.markdown("<hr>", unsafe_allow_html=True)

        # ----------------------------------------------------
        # NETWORK VISUALIZATIONS SECTION
        # ----------------------------------------------------
        # ----------------------------------------------------
        # NETWORK VISUALIZATIONS SECTION
        # ----------------------------------------------------
        st.markdown("#### Interactive Network Visualizations")

        viz_type = st.selectbox(
            "Select Graph Type to Visualize:",
            [
                "Bipartite Shareholder-Stock Graph",
                "One-Mode Stock-Stock Projection Graph",
            ],
        )

        if viz_type == "Bipartite Shareholder-Stock Graph":
            st.markdown(
                "Use the slider to filter the network degree to see the core structures."
            )

            # Slider to filter shareholder degree
            min_degree = st.slider(
                "Filter Shareholders by Min Holdings (Degree):",
                min_value=1,
                max_value=10,
                value=5,
            )

            # Subgraph selection
            filtered_shareholders = [
                node
                for node, data in G.nodes(data=True)
                if data.get("type") == "shareholder"
                and G.degree(node) >= min_degree
            ]

            filtered_nodes = list(filtered_shareholders) + list(stocks)
            subG = G.subgraph(filtered_nodes).copy()

            # Remove isolated nodes to clean up graph
            isolated_nodes = [
                node for node in subG.nodes() if subG.degree(node) == 0
            ]
            subG.remove_nodes_from(isolated_nodes)

            if subG.number_of_nodes() == 0:
                st.warning("No nodes match the filter criteria.")
            else:
                # Layout
                pos = nx.spring_layout(subG, k=0.25, iterations=60, seed=42)

                # Edges trace
                edge_x = []
                edge_y = []
                for edge in subG.edges():
                    x0, y0 = pos[edge[0]]
                    x1, y1 = pos[edge[1]]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])

                edge_trace = go.Scatter(
                    x=edge_x,
                    y=edge_y,
                    line=dict(width=0.6, color="#CBD5E1"),
                    hoverinfo="none",
                    mode="lines",
                )

                # Stock Node trace
                stock_x = []
                stock_y = []
                stock_text = []
                for node in subG.nodes():
                    if subG.nodes[node]["type"] == "stock":
                        x, y = pos[node]
                        stock_x.append(x)
                        stock_y.append(y)
                        stock_text.append(node)

                stock_trace = go.Scatter(
                    x=stock_x,
                    y=stock_y,
                    mode="markers+text",
                    text=stock_text,
                    textposition="top center",
                    hoverinfo="text",
                    hovertext=[
                        f"Stock: {node}<br>Top Shareholders: {G.degree(node)}"
                        for node in stock_text
                    ],
                    marker=dict(
                        symbol="square",
                        size=15,
                        color="#1E3A8A",
                        line=dict(width=1, color="#1E40AF"),
                    ),
                )

                # Shareholder Node trace
                sh_x = []
                sh_y = []
                sh_hover = []
                for node in subG.nodes():
                    if subG.nodes[node]["type"] == "shareholder":
                        x, y = pos[node]
                        sh_x.append(x)
                        sh_y.append(y)
                        deg = G.degree(node)
                        sh_hover.append(
                            f"Shareholder: {node}<br>Holds {deg} SET50 Stock(s)"
                        )

                sh_trace = go.Scatter(
                    x=sh_x,
                    y=sh_y,
                    mode="markers",
                    hoverinfo="text",
                    hovertext=sh_hover,
                    marker=dict(
                        symbol="circle",
                        size=12,
                        color="#EF4444",
                        line=dict(width=1, color="#DC2626"),
                    ),
                )

                # Figure
                fig_net = go.Figure(
                    data=[edge_trace, sh_trace, stock_trace],
                    layout=go.Layout(
                        showlegend=False,
                        hovermode="closest",
                        margin=dict(b=10, l=5, r=5, t=10),
                        xaxis=dict(
                            showgrid=False, zeroline=False, showticklabels=False
                        ),
                        yaxis=dict(
                            showgrid=False, zeroline=False, showticklabels=False
                        ),
                        plot_bgcolor="white",
                        height=550,
                    ),
                )
                st.plotly_chart(fig_net, use_container_width=True)
                st.caption(
                    "🔵 Blue Squares represent Stock Tickers. 🔴 Red Circles represent Major Shareholders. Zoom and drag to explore."
                )

        else:
            st.markdown(
                "This projection connects two stocks if they share at least one common top 5 major shareholder. "
                "The edge width and color represent the number of shared major shareholders. "
                "This reveals institutional ownership overlap clusters across industries."
            )

            # Slider for min weight (shared shareholders)
            min_shared = st.slider(
                "Filter Stock Connections by Min Shared Shareholders:",
                min_value=1,
                max_value=5,
                value=1,
            )

            # Filter G_stock by edge weight
            subG_stock = nx.Graph()
            for u, v in G_stock.edges():
                # Calculate shared shareholders count
                shared_sh = list(nx.common_neighbors(G, u, v))
                weight = len(shared_sh)
                if weight >= min_shared:
                    subG_stock.add_node(u, type="stock")
                    subG_stock.add_node(v, type="stock")
                    subG_stock.add_edge(u, v, weight=weight, shared=shared_sh)

            if subG_stock.number_of_nodes() == 0:
                st.warning("No stock connections match the filter criteria.")
            else:
                pos_stock = nx.spring_layout(
                    subG_stock, k=0.3, iterations=60, seed=42
                )

                # Edges trace
                edge_x = []
                edge_y = []
                for u, v, d in subG_stock.edges(data=True):
                    x0, y0 = pos_stock[u]
                    x1, y1 = pos_stock[v]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])

                edge_trace_stock = go.Scatter(
                    x=edge_x,
                    y=edge_y,
                    line=dict(width=1.5, color="#94A3B8"),
                    hoverinfo="none",
                    mode="lines",
                )

                # Node trace
                node_x = []
                node_y = []
                node_text = []
                node_color = []
                node_size = []

                for node in subG_stock.nodes():
                    x, y = pos_stock[node]
                    node_x.append(x)
                    node_y.append(y)
                    node_text.append(node)
                    deg = subG_stock.degree(node)
                    node_color.append(deg)
                    node_size.append(15)

                node_trace_stock = go.Scatter(
                    x=node_x,
                    y=node_y,
                    mode="markers+text",
                    text=node_text,
                    textposition="top center",
                    hoverinfo="text",
                    hovertext=[
                        f"Stock: {node}<br>Connected to {subG_stock.degree(node)} other stock(s)"
                        for node in node_text
                    ],
                    marker=dict(
                        showscale=True,
                        colorscale="Viridis",
                        reversescale=False,
                        color=node_color,
                        size=node_size,
                        colorbar=dict(
                            thickness=15,
                            title=dict(text="Overlap Degree", side="right"),
                            xanchor="left",
                        ),
                        line=dict(width=1.5, color="#1E293B"),
                    ),
                )

                fig_stock = go.Figure(
                    data=[edge_trace_stock, node_trace_stock],
                    layout=go.Layout(
                        showlegend=False,
                        hovermode="closest",
                        margin=dict(b=10, l=5, r=5, t=10),
                        xaxis=dict(
                            showgrid=False, zeroline=False, showticklabels=False
                        ),
                        yaxis=dict(
                            showgrid=False, zeroline=False, showticklabels=False
                        ),
                        plot_bgcolor="white",
                        height=550,
                    ),
                )
                st.plotly_chart(fig_stock, use_container_width=True)
                st.caption(
                    "Each node is a stock ticker. Edge connects stocks with shared shareholders. Larger/brighter nodes have more sharing relationships."
                )

        st.markdown("<hr>", unsafe_allow_html=True)

        with st.expander("📊 View Complete Bipartite Network SNA Metrics Table", expanded=False):
            st.markdown(
                "Network centralities describe the structural properties of each node in the stock market."
            )

            # Compile DataFrame
            net_df_list = []
            for node in G.nodes():
                net_df_list.append(
                    {
                        "Node Name": node,
                        "Type": "Shareholder"
                        if G.nodes[node]["type"] == "shareholder"
                        else "Stock",
                        "Holdings Count (Degree)": G.degree(node),
                        "Degree Centrality": deg_cent.get(node, 0),
                        "Betweenness Centrality": between_cent.get(node, 0),
                        "Eigenvector Centrality": eigen_cent.get(node, 0),
                    }
                )

            net_metrics_df = pd.DataFrame(net_df_list)

            # Sort option
            sort_by = st.selectbox(
                "Sort centrality metrics by:",
                [
                    "Degree Centrality",
                    "Betweenness Centrality",
                    "Eigenvector Centrality",
                    "Holdings Count (Degree)",
                ],
            )

            sorted_metrics = net_metrics_df.sort_values(by=sort_by, ascending=False)

            # Formatted table
            formatted_metrics = sorted_metrics.copy()
            formatted_metrics["Degree Centrality"] = formatted_metrics[
                "Degree Centrality"
            ].apply(lambda x: f"{x:.4f}")
            formatted_metrics["Betweenness Centrality"] = formatted_metrics[
                "Betweenness Centrality"
            ].apply(lambda x: f"{x:.4f}")
            formatted_metrics["Eigenvector Centrality"] = formatted_metrics[
                "Eigenvector Centrality"
            ].apply(lambda x: f"{x:.4f}")

            st.dataframe(formatted_metrics, use_container_width=True, hide_index=True)

            # Definitions
            st.markdown("""
            **SNA Terms Definition**:
            *   **Degree Centrality**: Ratio of nodes connected to this node. For shareholders, it denotes portfolio diversification.
            *   **Betweenness Centrality**: Measures how often a node acts as a 'bridge' along shortest paths. High stock betweenness implies it connects unique investor groups.
            *   **Eigenvector Centrality**: Measures influence. A node is influential if it connects to other well-connected (influential) nodes.
            """)
