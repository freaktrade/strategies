# --- Do not remove these libs ---
from freqtrade.strategy.interface import IStrategy
from typing import Dict, List
from functools import reduce
from pandas import DataFrame
# --------------------------------

import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from typing import Dict, List
from functools import reduce
from pandas import DataFrame, DatetimeIndex, merge
# --------------------------------

import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy  # noqa

class YouPig(IStrategy):
    
    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi"
    minimal_roi = {
        "0": 0.1
    }

    # Optimal stoploss designed for the strategy
    # This attribute will be overridden if the config file contains "stoploss"
    stoploss = -0.035
    trailing_stop = True
    trailing_stop_positive = 0.001
    trailing_stop_positive_offset = 0.003
    trailing_only_offset_is_reached = True

    # Optimal ticker interval for the strategy
    ticker_interval = '5m'

    order_types = {
    'buy': 'limit',
    'sell': 'limit',
    'emergencysell': 'market',
    'stoploss': 'limit',
    'stoploss_on_exchange': True,
    'stoploss_on_exchange_interval': 60,
    'stoploss_on_exchange_limit_ratio': 0.99
}

   
    # resample factor to establish our general trend. Basically don't buy if a trend is not given
    resample_factor = 12
    resample_factor2 = 48

    EMA_SHORT_TERM = 5
    EMA_MEDIUM_TERM = 10
    EMA_LONG_TERM = 20
    EMA_XTRA_LONG_TERM = 200

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = self.resample(dataframe, self.ticker_interval, self.resample_factor)

        ##################################################################################
        # buy and sell indicators

        dataframe['ema_{}'.format(self.EMA_SHORT_TERM)] = ta.EMA(
            dataframe, timeperiod=self.EMA_SHORT_TERM
        )
        dataframe['ema_{}'.format(self.EMA_MEDIUM_TERM)] = ta.EMA(
            dataframe, timeperiod=self.EMA_MEDIUM_TERM
        )
        dataframe['ema_{}'.format(self.EMA_LONG_TERM)] = ta.EMA(
            dataframe, timeperiod=self.EMA_LONG_TERM
        )
         


        

        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), window=20, stds=2
        )
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']

        dataframe['min'] = ta.MIN(dataframe, timeperiod=self.EMA_MEDIUM_TERM)
        dataframe['max'] = ta.MAX(dataframe, timeperiod=self.EMA_MEDIUM_TERM)

        dataframe['cci'] = ta.CCI(dataframe)
        dataframe['mfi'] = ta.MFI(dataframe)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=7)

        dataframe['average'] = (dataframe['close'] + dataframe['open'] + dataframe['high'] + dataframe['low']) / 4

        ####################################################################################
        dataframe['ema5'] = ta.EMA(dataframe, timeperiod=5)
        dataframe['ema12'] = ta.EMA(dataframe, timeperiod=12)
        dataframe['ema20'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)


        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        ##################################################################################
        # required for graphing
        bollinger = qtpylib.bollinger_bands(dataframe['close'], window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_upperband'] = bollinger['upper']
        dataframe['bb_middleband'] = bollinger['mid']

        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the buy signal for the given dataframe
        :param dataframe: DataFrame
        :return: DataFrame with buy column
        """
        dataframe.loc[
            (
                    (
                            (
                                    
                                     # (dataframe['average'].shift(5) > dataframe['average'].shift(4))
                                     (dataframe['average'].shift(4) > dataframe['average'].shift(3))
                                    &(dataframe['average'].shift(3) > dataframe['average'].shift(2))
                                    & (dataframe['average'].shift(2) > dataframe['average'].shift(1))
                                    & (dataframe['average'].shift(1) < dataframe['average'].shift(0))
                                    & (dataframe['low'].shift(1) < dataframe['bb_middleband'])
                                    & (dataframe['cci'].shift(1) < -100)
                                    & (dataframe['rsi'].shift(1) < 30)
                                    & (dataframe['mfi'].shift(1) > 20)
                                    
                            )
                            |
                            # simple v bottom shape (lopsided to the left to increase reactivity)
                            # which has to be below a very slow average
                            # this pattern only catches a few, but normally very good buy points
                            (
                                     (dataframe['close'] > dataframe['ema200'])
                                    &(dataframe['ema_{}'.format(self.EMA_SHORT_TERM, self.resample_factor2)] < dataframe['ema_{}'.format(self.EMA_MEDIUM_TERM, self.resample_factor2)]) 
                                    &(dataframe['ema_{}'.format(self.EMA_LONG_TERM, self.resample_factor2)] > dataframe['ema_{}'.format(self.EMA_MEDIUM_TERM, self.resample_factor2)])
                                    #&(dataframe['close'] < dataframe['ema_{}'.format(self.EMA_LONG_TERM, self.resample_factor2)]) 
                                    &(dataframe['ema_{}'.format(self.EMA_SHORT_TERM)] < dataframe['ema_{}'.format(self.EMA_LONG_TERM)]) 
                                    &(dataframe['ema_{}'.format(self.EMA_LONG_TERM)] > dataframe['ema_{}'.format(self.EMA_MEDIUM_TERM)]) 
                                    &(dataframe['close'].shift(0) > dataframe['open'].shift(0)) 
                                    &(dataframe['close'].shift(1) < dataframe['open'].shift(1))
                                    #&(dataframe['ema20'] > dataframe['ema5']*1.003)
                                    &(dataframe['ema20'] > dataframe['ema12']*1.0035)
                                    & (dataframe['low'].shift(1) < dataframe['bb_lowerband'])
                                    & (dataframe['low'] < dataframe['bb_lowerband'])
                                    & (dataframe['close'].shift(1) == dataframe['min'])

                            )
                    )
                    # safeguard against down trending markets and a pump and dump
                    &
                    (
                            
                            (dataframe['volume'] < (dataframe['volume'].rolling(window=30).mean().shift(1) * 20)) &
                            (dataframe['resample_sma'] < dataframe['close']) &
                            (dataframe['resample_sma'].shift(1) < dataframe['resample_sma'])
                    )
            )
            ,
            'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the sell signal for the given dataframe
        :param dataframe: DataFrame
        :return: DataFrame with buy column
        """
        dataframe.loc[
            (
                    (dataframe['close'] > dataframe['ema_{}'.format(self.EMA_SHORT_TERM)]) &
                    (dataframe['close'] > dataframe['ema_{}'.format(self.EMA_MEDIUM_TERM)]) &
                    (dataframe['close'] >= dataframe['max']) &
                    (dataframe['close'] >= dataframe['bb_upperband']) &
                    (dataframe['mfi'] > 80)
            ) |

            # always sell on eight green candles
            # with a high rsi
            (
                    (dataframe['open'] < dataframe['close']) &
                    (dataframe['open'].shift(1) < dataframe['close'].shift(1)) &
                    (dataframe['open'].shift(2) < dataframe['close'].shift(2)) &
                    (dataframe['open'].shift(3) < dataframe['close'].shift(3)) &
                    (dataframe['open'].shift(4) < dataframe['close'].shift(4)) &
                    (dataframe['open'].shift(5) < dataframe['close'].shift(5)) &
                    (dataframe['open'].shift(6) < dataframe['close'].shift(6)) &
                    (dataframe['open'].shift(7) < dataframe['close'].shift(7)) &
                    (dataframe['rsi'] > 70)
            )
            ,
            'sell'
        ] = 1
        return dataframe

    def resample(self, dataframe, interval, factor):
        # defines the reinforcement logic
        # resampled dataframe to establish if we are in an uptrend, downtrend or sideways trend
        df = dataframe.copy()
        df = df.set_index(DatetimeIndex(df['date']))
        ohlc_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }
        df = df.resample(str(int(interval[:-1]) * factor) + 'min',
                         label="right").agg(ohlc_dict).dropna(how='any')
        df['resample_sma'] = ta.SMA(df, timeperiod=25, price='close')
        df = df.drop(columns=['open', 'high', 'low', 'close'])
        df = df.resample(interval[:-1] + 'min')
        df = df.interpolate(method='time')
        df['date'] = df.index
        df.index = range(len(df))
        dataframe = merge(dataframe, df, on='date', how='left')
        return dataframe
