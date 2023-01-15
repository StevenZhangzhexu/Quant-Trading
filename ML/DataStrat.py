import numpy as np
import pandas as pd
import yfinance as yf

# Create the class for data extraction and preprocessing based on moving avergae stratrgy 
class DataPrecessor():

    # Initialize the class
    def __init__(self, symbol, start_date, end_date, direction = "long_short", short_period = 12, long_period = 21):
        self.df = self._extract_data(symbol, start_date, end_date)
        self.sharpe = 0
        self.direction = direction
        self.short_period = short_period
        self.long_period = long_period
        self.backtest_ma_crossover()

    # Extract data
    def _extract_data(self, symbol, start_date, end_date):
        data = yf.download(symbol,start_date,end_date)
        data = data[["Open", "High", "Low", "Close", "Volume"]]
        data = self._structure_df(data)
        return data

    def _structure_df(self, df, t_steps = [1, 2]):
        """
        Calculates general period returns and volatility.
        """
        # Day of Week
        df["DOW"] = df.index.dayofweek
        # Returns
        df["Returns"] = df["Close"].pct_change()
        # 30 Days Rolling Return
        df["Roll_Rets"] = df["Returns"].rolling(window=30).sum()
        # Range
        df["Range"] = df["High"] / df["Low"] - 1
        # 30 Days Avarage Range
        df["Avg_Range"] = df["Range"].rolling(window=30).mean()
        # Relative Strength Index
        df["RSI"] = self.rsi(df)
        df["RSI_Ret"] = df["RSI"] / df["RSI"].shift(1)
        # cumulative log return 
        df["Bench_C_Rets"], sharpe = self._calculate_returns(df, True)
        # Add Time Intervals for T1, T2 data
        t_features = ["Returns", "Range", "RSI_Ret"]
        for ts in t_steps:
            for tf in t_features:
                df[f"{tf}_T{ts}"] = df[tf].shift(ts)
        self.sharpe = sharpe
        df.dropna(inplace=True)
        return df
 
    def _set_signal(self):
        """
        Adjusts the signal to represent our strategy.
        """
        if self.direction == "long":
            pos_multiplier = 1
            neg_multiplier = 0
        elif self.direction == "long_short":
            pos_multiplier = 1
            neg_multiplier = -1
        else:
            pos_multiplier = 0
            neg_multiplier = -1
        return pos_multiplier, neg_multiplier
 
    def _calculate_returns(self, df, is_benchmark):
        """
        Calculates returns for equity curve.
        """
        # Calculate multiplier
        if not is_benchmark:
            multiplier_1 = df["Signal"]
            multiplier_2 = 1 if "PSignal" not in df.columns else df["PSignal"]
            log_rets = np.log(df["Close"] / df["Close"].shift(1)) * multiplier_1 * multiplier_2
        else:
            multiplier_1 = 1
            multiplier_2 = 1
            
            # Assume open price on following day to avoid lookahead bias for close calculation
            log_rets = np.log(df["Open"].shift(-1) / df["Close"].shift(1)) * multiplier_1 * multiplier_2
        
        # Calculate Sharpe Ratio
        sharpe_ratio = self.sharpe_ratio(log_rets)
        
        # Calculate Cumulative Returns
        c_log_rets = log_rets.cumsum()
        c_log_rets_exp = np.exp(c_log_rets) - 1
        
        # Return result and Sharpe ratio
        return c_log_rets_exp, sharpe_ratio
    
    def sharpe_ratio(self, return_series):
        """
        Calculates sharpe_ratio for equity curve.
        """
        N = 365 # Trading days in the year is 365 for crypto
        rf = 0.005 # Half a percent risk free rare
        mean = return_series.mean() * N -rf
        sigma = return_series.std() * np.sqrt(N)
        sharpe = round(mean / sigma, 3)
        return sharpe

    def rsi(self, df, periods = 14, ema = True):
        """
        Calculates relative strength index.
        """
        close_delta = df['Close'].diff()

        # Make two series: one for lower closes and one for higher closes
        up = close_delta.clip(lower=0)
        down = -1 * close_delta.clip(upper=0)
        
        if ema == True:
            # Use exponential moving average
            ma_up = up.ewm(com = periods - 1, adjust=True, min_periods = periods).mean()
            ma_down = down.ewm(com = periods - 1, adjust=True, min_periods = periods).mean()
        else:
            # Use simple moving average
            ma_up = up.rolling(window = periods, adjust=False).mean()
            ma_down = down.rolling(window = periods, adjust=False).mean()
            
        rsi = 100 - (100/(1 + ma_up / ma_down))
        return rsi


    def change_df(self, new_df, drop_cols=[]):
        """
        Replace Dataframe.
        """
        new_df = new_df.drop(columns=drop_cols)
        self.df = new_df

    def backtest_ma_crossover(self, drop_cols=[]):
        """
        Moving average crossover strategy.
        """
        # Set variables 
        df = self.df
        period_1 = self.short_period
        period_2 = self.long_period
        
        # Get multipliers
        pos_multiplier, neg_multiplier = self._set_signal()
            
        # Calculate Moving Averages
        if f"MA_{period_1}" or f"MA_{period_2}" not in df.columns:
            df[f"MA_{period_1}"] = df["Close"].rolling(window=period_1).mean()
            df[f"MA_{period_2}"] = df["Close"].rolling(window=period_2).mean()
            df.dropna(inplace=True)
        
        # Calculate Benchmark Returns
        df["Bench_C_Rets"], sharpe_ratio_bench = self._calculate_returns(df, True)
        
        # Calculate Signal
        # Golden Cross
        df.loc[df[f"MA_{period_1}"] > df[f"MA_{period_2}"], "Signal"] = pos_multiplier
        # Death Cross
        df.loc[df[f"MA_{period_1}"] <= df[f"MA_{period_2}"], "Signal"] = neg_multiplier
        
        # Calculate Strategy Returns
        df["Strat_C_Rets"], sharpe_ratio_strat = self._calculate_returns(df, False)
        
        # Get values for output
        bench_rets = df["Bench_C_Rets"].values.astype(float)
        strat_rets = df["Strat_C_Rets"].values.astype(float)
        print("Sense check: ", round(df["Close"].values[-1] / df["Close"].values[0] - 1, 3), round(bench_rets[-1], 3))
        
        # Remove irrelevant features
        if len(drop_cols) > 0:
            df = df.drop(columns=drop_cols)
        
        # Ensure Latest DF matches
        df = df.dropna()
        self.df = df
        
        # Return df
        return df, sharpe_ratio_bench, sharpe_ratio_strat