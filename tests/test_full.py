import os
from io import BytesIO

import numpy as np

from amodem import send
from amodem import recv
from amodem import common
from amodem import sigproc
from amodem import sampling

import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-12s %(message)s')


class Args(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def run(size, chan=None, df=0):
    tx_data = os.urandom(size)
    tx_audio = BytesIO()
    send.main(Args(silence_start=1, silence_stop=1,
              input=BytesIO(tx_data), output=tx_audio))

    data = tx_audio.getvalue()
    data = common.loads(data)
    if chan is not None:
        data = chan(data)
    if df:
        sampler = sampling.Sampler(data, sampling.Interpolator())
        sampler.freq += df
        data = sampler.take(len(data))

    data = common.dumps(data)
    rx_audio = BytesIO(data)

    rx_data = BytesIO()
    recv.main(Args(skip=100, input=rx_audio, output=rx_data))
    rx_data = rx_data.getvalue()

    assert rx_data == tx_data


def test_small():
    run(1024, chan=lambda x: x)


def test_frequency_error():
    for df in [1, -1, 10, -10]:
        run(1024, df=df*1e-6)


def test_lowpass():
    run(1024, chan=lambda x: sigproc.lfilter(b=[0.9], a=[1.0, -0.1], x=x))


def test_highpass():
    run(1024, chan=lambda x: sigproc.lfilter(b=[0.9], a=[1.0, 0.1], x=x))


def test_attenuation():
    run(5120, chan=lambda x: x * 0.1)


def test_low_noise():
    r = np.random.RandomState(seed=0)
    run(5120, chan=lambda x: x + r.normal(size=len(x), scale=0.0001))


def test_medium_noise():
    r = np.random.RandomState(seed=0)
    run(5120, chan=lambda x: x + r.normal(size=len(x), scale=0.001))


def test_large():
    run(54321, chan=lambda x: x)

