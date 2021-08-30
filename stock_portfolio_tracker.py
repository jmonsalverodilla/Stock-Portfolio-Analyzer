#Libraries
import base64
import datetime
from io import BytesIO, StringIO
import os
import pandas as pd
import streamlit as st
import plotly
import yfinance as yf

from technical_analysis import download_data, portfolio_return, benchmark_return, wealth_plot,accumulated_return_plot, drawdawn_plot, allocation_plot, day_returns_plot
from fundamental_analysis import market_cap, annual_financials, quarter_income_statement, calculate_ratios, market_cap_plot, bar_plot, line_plot

#Downloader
def export_plotly_image_link(fig,path_file):
    mybuff = StringIO()
    fig.write_html(mybuff, include_plotlyjs='cdn')
    mybuff = BytesIO(mybuff.getvalue().encode())
    b64 = base64.b64encode(mybuff.read()).decode()
    #plotly.offline.plot(fig, filename=path_file, auto_open=False)
    href = f'<a href="data:text/html;charset=utf-8;base64, {b64}" download="{os.path.basename(path_file)}">Download plot</a>'
    return href

def export_plotly_image_button(fig,path_file):
    plotly.offline.plot(fig, filename = path_file, auto_open=True)

def save_all(path_file):
    with open(path_file, 'a') as f:
        f.write(fig_wealth_plot.to_html(full_html=False, include_plotlyjs='cdn'))
        f.write(fig_accumulated_return.to_html(full_html=False, include_plotlyjs='cdn'))
        f.write(fig_drawdawn.to_html(full_html=False, include_plotlyjs='cdn'))
        f.write(fig_day_returns.to_html(full_html=False, include_plotlyjs='cdn'))
        f.write(fig_allocation.to_html(full_html=False, include_plotlyjs='cdn'))

######################STREAMLIT APP##############
st.set_page_config(layout="wide",initial_sidebar_state='expanded',page_title="Stock Portfolio Tracker")
st.write('<style>div.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)
st.write("# PORTFOLIO ANALYSIS ")

##################PROXY OPTION###############
st.markdown("### Behind proxy server")
proxy_option = st.radio(label='Proxy server', options=['No','Yes'])

##########TECHNICAL OR FUNDAMENTAL###########
analysis_type = st.sidebar.radio("Choose an info type",('Technical', 'Fundamental'))

###PORTFOLIO COMPOSITION###
st.markdown("### Select the stocks that will make up your portfolio")
sp500 = pd.read_csv("./dat/all_tickers.csv")[['Symbol']]
symbols = sp500['Symbol'].sort_values().tolist()

big_fish = ['AAPL','AMZN','GOOGL','MSFT']

portfolio_companies = st.multiselect(label="Selected stocks", options = list(symbols),
                                     default=big_fish)

###BENCHMARK OPTIONALITY AND PORTFOLIO ALLOCATION###
if analysis_type== 'Technical':
    ###DATE RANGE###
    today = datetime.date.today()
    min_value = today - datetime.timedelta(days=20000)
    before = today - datetime.timedelta(days=2555)

    start_date = st.sidebar.date_input('Start date', before, min_value=min_value)
    end_date = st.sidebar.date_input('End date', today, min_value=min_value)

    if start_date > end_date:
        st.sidebar.error('Error: End date must fall after start date.')
    ###INITIAL INVESTMENT###
    st.markdown("### Select your initial investment ($)")
    initial_investment = st.slider(label='Initial investment ($)', key='Initial investment', value=10_000, min_value=1_000, max_value=100_000, step=1_000)
    ###BENCHMARK OPTIONALITY###
    st.markdown("### Benchmark index")
    benchmark_option = st.radio(label='Benchmark', options=['None','S&P 500', 'Nasdaq Composite', 'Both'])

    ###PORTFOLIO ALLOCATION###
    st.sidebar.markdown("Do you want an equally balanced porfolio?")
    allocation = st.sidebar.selectbox('Select', ['Yes','No'])
    if len(portfolio_companies)>=1:
        if allocation=='Yes':
            company_weighs = [1 / len(portfolio_companies)] * len(portfolio_companies)
        else:
            st.sidebar.markdown("Select the percentage allocated to each company (%)")
            company_weigh_balanced = 1/len(portfolio_companies)
            company_weighs = []
            for company in portfolio_companies:
                company_weigh = st.sidebar.number_input(company, value = company_weigh_balanced, min_value=0.0, max_value=1.0, step=0.01)
                company_weighs.append(company_weigh)
    else:
        pass

###APP##
proxy_server = os.getenv('PROXY_SERVER')
if st.button("Analyze portfolio",key='1'):
    if len(portfolio_companies)==0:
        st.warning("Introduce at least a company ticker")
    else:
        ########################################################FUNDAMENTAL###################################
        if analysis_type == "Fundamental":
            with st.spinner(text='In progress: it could take a few seconds.'):
                #####################################################DATA###########################################################
                ##### TICKERS ######
                dict_tickers = {}
                for ticker in portfolio_companies:
                    dict_tickers[ticker] = yf.Ticker(ticker)

                ######### MARKET CAPITALIZATION ############
                df_market_cap = market_cap(dict_tickers, proxy_option)
                market_cap_columns = df_market_cap.loc[:, df_market_cap.columns.str.contains('Market_cap')].columns
                df_market_cap = df_market_cap[market_cap_columns]

                ######## QUARTER INCOME STATEMENT ############
                df_quarter_income_statement,df_annual_income_statement_forecasted = quarter_income_statement(dict_tickers)

                ######### ANNUAL FINANCIALS ################
                df_annual_financials = annual_financials(dict_tickers)
                df_annual_financials = pd.concat([df_annual_income_statement_forecasted,df_annual_financials]).reset_index(drop=['index'])
                df_annual_financials = pd.concat([df_annual_financials,df_market_cap],axis=1)
                df_annual_financials = df_annual_financials.fillna(method='bfill')

                ####### RATIOS ###########################
                df_complete_annual = calculate_ratios(df_annual_financials,dict_tickers)
                st.write(df_complete_annual)

                #######################################################PLOTS#############################################################
                ##################MARKET CAP METRICS################
                st.markdown(f"<h1 style='text-align: center; color: #3E477F;'> MARKET CAP METRICS </h1>", unsafe_allow_html=True)
                fig_market_cap, dict_stock_color = market_cap_plot(df_complete_annual, period='Annually',
                                                                   substring="Market_cap", y_title="Market cap ($)", general_title="Market cap (B$) over time")
                st.plotly_chart(fig_market_cap)


                #################REVENUE METRICS#####################
                st.markdown(f"<h1 style='text-align: center; color: #3E477F;'> REVENUE METRICS </h1>", unsafe_allow_html=True)
                #REVENUE PLOT#
                fig_revenue_plot_annual = bar_plot(df_complete_annual, dict_stock_color=dict_stock_color,period = 'Annually',
                                                   substring="Revenue",y_title="Revenue (B$)",general_title="Revenue (B$) over time")
                st.plotly_chart(fig_revenue_plot_annual)

                # REVENUE NORMALIZED PLOT#
                fig_normalized_revenue_plot_annual = line_plot(df_complete_annual, dict_stock_color=dict_stock_color, period='Annually',
                                                               substring="Normalized_revenue", y_title="Normalized revenue", general_title = "Normalized revenue since beginning of period")
                st.plotly_chart(fig_normalized_revenue_plot_annual)

                # P/S PLOT#
                fig_price_to_sales = line_plot(df_complete_annual,  dict_stock_color=dict_stock_color, period='Annually',
                                               substring="P/S", y_title = "P/S multiple", general_title = "P/S since beginning of period")
                st.plotly_chart(fig_price_to_sales)

                #REVENUE GROWTH PLOT#
                #fig_growth_revenue_plot_annual = bar_plot(df_complete_annual, dict_stock_color = dict_stock_color, period='Annually',
                #                                          substring="Growth_revenue", y_title="Revenue growth", general_title = "Revenue growth year-over-year")
                #st.plotly_chart(fig_growth_revenue_plot_annual)

                # REVENUE PLOT (QUARTER)#
                fig_revenue_plot_quarter = bar_plot(df_quarter_income_statement, dict_stock_color=dict_stock_color, period='Quarterly',
                                                    substring="Revenue", y_title="Revenue (B$)", general_title="Revenue (B$) over time")
                st.plotly_chart(fig_revenue_plot_quarter)


                ################GROSS PROFIT METRICS#################
                st.markdown(f"<h1 style='text-align: center; color: #3E477F;'> GROSS PROFIT METRICS </h1>", unsafe_allow_html=True)
                # GROSS PROFIT PLOT#
                fig_gross_profit_plot_annual = bar_plot(df_complete_annual, dict_stock_color=dict_stock_color, period='Annually',
                                                  substring="Gross_profit", y_title="Gross profit ($)", general_title="Gross profit year-over-year")
                st.plotly_chart(fig_gross_profit_plot_annual)

                # GROSS PROFIT NORMALIZED PLOT#
                fig_normalized_gross_profit_plot_annual = line_plot(df_complete_annual, dict_stock_color=dict_stock_color, period='Annually',
                                                                  substring="Normalized_gross_profit", y_title="Normalized gross profit", general_title="Normalized gross profit since beginning of period")
                st.plotly_chart(fig_normalized_gross_profit_plot_annual)

                # P/GROSS_PROFIT PLOT#
                fig_price_to_gross_profit = line_plot(df_complete_annual, dict_stock_color=dict_stock_color, period='Annually',
                                                  substring="P/G", y_title="P/Gross profit multiple", general_title="P/Gross profit since beginning of period")
                st.plotly_chart(fig_price_to_gross_profit)

                # GROSS PROFIT GROWTH PLOT#
                #fig_growth_gross_profit_plot_annual = bar_plot(df_complete_annual, period='Annually', dict_stock_color=dict_stock_color,
                #                                         substring="Growth_gross_profit", y_title="Gross profit growth", general_title="Gross profit growth year-over-year")
                #st.plotly_chart(fig_growth_gross_profit_plot_annual)

                # GROSS PROFIT PLOT (QUARTER)#
                fig_gross_profit_plot_quarter = bar_plot(df_quarter_income_statement, dict_stock_color=dict_stock_color, period='Quarterly',
                                                   substring="Gross_profit", y_title="Gross profit ($)", general_title="Gross profit quarter-over-quarter")
                st.plotly_chart(fig_gross_profit_plot_quarter)



                ##############NET INCOME METRICS#####################
                st.markdown(f"<h1 style='text-align: center; color: #3E477F;'> NET INCOME METRICS </h1>", unsafe_allow_html=True)
                #NET INCOME PLOT#
                fig_income_plot_annual = bar_plot(df_complete_annual, dict_stock_color = dict_stock_color, period='Annually',
                                                  substring="Net_income",y_title="Net income ($)",general_title="Net income year-over-year")
                st.plotly_chart(fig_income_plot_annual)

                # NET INCOME NORMALIZED PLOT#
                fig_normalized_net_income_plot_annual = line_plot(df_complete_annual,dict_stock_color=dict_stock_color, period='Annually',
                                                                  substring="Normalized_net_income", y_title="Normalized net income",general_title = "Normalized net income since beginning of period")
                st.plotly_chart(fig_normalized_net_income_plot_annual)

                #P/E PLOT#
                fig_price_to_earnings = line_plot(df_complete_annual, dict_stock_color=dict_stock_color,period='Annually',
                                                  substring="P/E", y_title = "P/E multiple", general_title="P/E since beginning of period")
                st.plotly_chart(fig_price_to_earnings)

                # NET INCOME GROWTH PLOT#
                #fig_growth_income_plot_annual = bar_plot(df_complete_annual, period='Annually', dict_stock_color=dict_stock_color,
                #                                    substring="Growth_net_income", y_title="Net income growth", general_title="Net income growth year-over-year")
                #st.plotly_chart(fig_growth_income_plot_annual)

                # NET INCOME PLOT (QUARTER)#
                fig_income_plot_quarter = bar_plot(df_quarter_income_statement, dict_stock_color=dict_stock_color,period='Quarterly',
                                                   substring="Net_income",y_title="Net income ($)",general_title="Net income quarter-over-quarter")
                st.plotly_chart(fig_income_plot_quarter)


                ############RESEARCH & DEVELOPMENT METRICS#####
                st.markdown(f"<h1 style='text-align: center; color: #3E477F;'> RESEARCH & DEVELOPMENT METRICS </h1>", unsafe_allow_html=True)
                #RESEARCH & DEVELOPMENT#
                fig_research_plot_annual = line_plot(df_complete_annual, dict_stock_color=dict_stock_color, period='Annually',
                                                  substring="R&D/revenue", y_title="R&D/Revenue ratio", general_title="R&D/Revenue ratio year-over-year")
                st.plotly_chart(fig_research_plot_annual)


                ##############DEBT METRICS#####################
                st.markdown(f"<h1 style='text-align: center; color: #3E477F;'> DEBT METRICS </h1>", unsafe_allow_html=True)

                # CURRENT RATIO PLOT#
                fig_current_ratio = line_plot(df_complete_annual, period="Annually",dict_stock_color=dict_stock_color,
                                              substring="Current_ratio",y_title="Current ratio", general_title="Current ratio year-over-year")
                st.plotly_chart(fig_current_ratio)

                # DEBT-TO-EQUITY PLOT#
                fig_debt_to_equity = line_plot(df_complete_annual, period="Annually", dict_stock_color=dict_stock_color,
                                               substring="Debt/equity",y_title="Debt/Equity ratio", general_title="Debt/Equity ratio year-over-year")
                st.plotly_chart(fig_debt_to_equity)

                # DEBT-TO-EBIT PLOT#
                fig_debt_to_ebit = line_plot(df_complete_annual, period="Annually", dict_stock_color=dict_stock_color,
                                               substring="Debt/ebit", y_title="Debt/Ebit ratio", general_title="Debt/Ebit ratio year-over-year")
                st.plotly_chart(fig_debt_to_ebit)

                #stock = yf.Ticker("AYX")
                #if proxy_option == 'Yes':
                #    stock.get_info(proxy = proxy_server)
                #else:
                #    stock.get_info()
                #st.write(stock.major_holders)
                #st.write(stock.institutional_holders)
                #st.write(stock.recommendations)

        else:
            #1) Percentage allocation check
            if (sum(company_weighs)<= 0.99) | (sum(company_weighs) >= 1.01):
                st.warning("The sum of the percentages must be equal to 1")
            else:
                with st.spinner(text='In progress: it could take a few seconds.'):
                    dict_of_df, min_dates, error_tickers = download_data(portfolio_companies, start_date, end_date, proxy_option)
                    min_common_date = max(min_dates)
                    #2) Date check
                    delta_period = datetime.timedelta(5)
                    late_symbols = [symbol for symbol in list(dict_of_df.keys()) if dict_of_df[symbol]['Date'].min()>start_date+delta_period]
                    if start_date < min_common_date - delta_period:
                        if len(late_symbols)==1:
                            st.warning(f"The earliest common date for the portfolio is on the: {min_common_date.strftime('%d/%B/%Y')}. {late_symbols} was listed after the selected start date ({start_date}).")
                        else:
                            st.warning(f"The earliest common date for the portfolio is on the: {min_common_date.strftime('%d/%B/%Y')}. {late_symbols} were listed after the selected start date ({start_date}).")
                    company_list_df = list(dict_of_df.values())

                    #3) Ticker check
                    if len(error_tickers)!=0:
                        #If one symbol is delisted or not found, nothing is shown.
                        st.warning(f"{error_tickers} No data found, symbol may be delisted")
                    else:
                        day_returns = portfolio_return(company_list_df,
                                                       portfolio_companies,
                                                       initial_investment,
                                                       company_weighs,
                                                       start_date,
                                                       end_date
                                                       )
                        if benchmark_option == 'None':
                            benchmark_returns = day_returns[['Date']]
                        else:
                            if benchmark_option == 'S&P 500':
                                benchmark_names = ['^GSPC']
                                dict_of_benchmark,_,_  = download_data(benchmark_names, min_common_date, end_date, proxy_option)
                                benchmark_list_df = list(dict_of_benchmark.values())
                            elif benchmark_option == 'Nasdaq Composite':
                                benchmark_names = ['^IXIC']
                                dict_of_benchmark,_,_  = download_data(benchmark_names, min_common_date, end_date, proxy_option)
                                benchmark_list_df = list(dict_of_benchmark.values())
                            else:
                                benchmark_names = ['^GSPC', '^IXIC']
                                dict_of_benchmark,_,_ = download_data(benchmark_names, min_common_date, end_date, proxy_option)
                                benchmark_list_df = list(dict_of_benchmark.values())

                            benchmark_returns = benchmark_return(benchmark_list_df,
                                                                 benchmark_names,
                                                                 initial_investment)

                        #WEALTH PLOT#
                        fig_wealth_plot = wealth_plot(day_returns,benchmark_returns)
                        st.plotly_chart(fig_wealth_plot)
                        st.markdown(export_plotly_image_link(fig_wealth_plot ,path_file="./output/wealth_plot.html"), unsafe_allow_html=True)

                        #DF#
                        cumulative_return = day_returns['Return_acumulado_total'].tail(1).values[0] / 100
                        annualized_return = ((1 + cumulative_return) ** (365 / day_returns.shape[0]) - 1) * 100
                        df = pd.DataFrame([[str(initial_investment)+"$",
                                            str(round(day_returns['Investment_acumulado_total'].tail(1).values[0],1))+"$",
                                            str(round(annualized_return,1))]],
                                          columns=['Initial investment ($)','Final investment ($)','Annualized return (%)'])
                        col1,col2,col3 = st.columns((5,10,5))
                        with col2:
                            st.write(df)

                        #ACCUMULATED RETURN PLOT#
                        fig_accumulated_return = accumulated_return_plot(day_returns, benchmark_returns)
                        st.plotly_chart(fig_accumulated_return)
                        st.markdown(export_plotly_image_link(fig_accumulated_return, path_file="./output/accumulated_return_plot.html"), unsafe_allow_html=True)

                        #DRAWDAWN PLOT#
                        fig_drawdawn = drawdawn_plot(day_returns, benchmark_returns)
                        st.plotly_chart(fig_drawdawn)
                        st.markdown(export_plotly_image_link(fig_drawdawn, path_file="./output/drawdawn_plot.html"), unsafe_allow_html=True)

                        # DAY RETURNS#
                        fig_day_returns = day_returns_plot(day_returns, benchmark_returns)
                        st.plotly_chart(fig_day_returns)
                        st.markdown(export_plotly_image_link(fig_day_returns, path_file="./output/day_returns_plot.html"), unsafe_allow_html=True)

                        #ALLOCATION PLOT#
                        fig_allocation = allocation_plot(day_returns)
                        st.plotly_chart(fig_allocation)
                        st.markdown(export_plotly_image_link(fig_allocation, path_file="./output/allocation_plot.html"), unsafe_allow_html=True)

                        ##SAVE ALL##
                        stocks_string = ''
                        for stock in portfolio_companies:
                            stocks_string = stocks_string + "_" + str(stock)
                        path = "./output"
                        path_file = f"./output/portfolio_{stocks_string}_{start_date}.html"
                        if os.path.exists(path):
                            save_all(path_file=path_file)
                        else:
                            os.makedirs(path)
                            save_all(path_file=path_file)


