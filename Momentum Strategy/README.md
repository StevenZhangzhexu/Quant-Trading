# The Moentum Strategy

This strategy combined **moentum**, **simple moving average** and **average true range as signal.** The strategy would buy stocks with top 20% momentum range and sell stocks if their price falls below **100 days MA** or they are not in top 20% stocks by momentum. Buying or selling amount is determined by current stock price and **average true range.**

## Metric

-   Sharpe Ratio, to compares the return of an investment with its risk.
-   Annual return of an investing strategy
-   Maximum drawdown of an investing strategy

## Back Testing

The moentum strategy was tested on past 3 years S&P 500 companies data (start date is 20191201 and end date is 20221201) where initial capital is 100000 and commission fee is set to 1%.

## Result

-   for moentum strategy:

![](images/outcome.png) ![](images/outcome_plot.png)

------------------------------------------------------------------------
