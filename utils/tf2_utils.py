import numpy as np
import tensorflow as tf


def show_graph(name='my_func_trace'):
    '''
    show tf2 graph in tensorboard. work for ppo, have bug in off-policy algorithm, like dqn..
    TODO: fix bug when showing graph of off-policy algorithm based on TF2.
    '''
    def show_tf2_graph(func):
        def inner(*args, **kwargs):
            tf.summary.trace_on(graph=True)
            ret = func(*args, **kwargs)
            tf.summary.trace_export(name=name)
            return ret
        return inner
    return show_tf2_graph


def get_TensorSpecs(*args):
    """
    get all inputs' shape in order to fix the problem of retracting in TF2.0
    """
    return [tf.TensorSpec(shape=[None] + i, dtype=tf.float32) for i in args]


def clip_nn_log_std(log_std, _min=-20, _max=2):
    """
    scale log_std from [-1, 1] to [_min, _max]
    Args:
        log_std: log standard deviation of a gaussian distribution
        _min: corrected minimum
        _max: corrected maximum
    Return:
        log_std after scaling, range from _min to _max
    """
    return _min + 0.5 * (_max - _min) * (log_std + 1)


def gaussian_reparam_sample(mu, log_std):
    """
    Reparameter
    Args:
        mu: mean value of a gaussian distribution
        log_std: log standard deviation of a gaussian distribution
    Return: 
        sample from the gaussian distribution
        the log probability of sample
    """
    std = tf.exp(log_std)
    pi = mu + tf.random.normal(mu.shape) * std
    log_pi = gaussian_likelihood(pi, mu, log_std)
    return pi, log_pi


def gaussian_clip_reparam_sample(mu, log_std, _min=-1, _max=1):
    """
    Reparameter sample and clip the value of sample to range [_min, _max]
    Args:
        mu: mean value of a gaussian distribution
        log_std: log standard deviation of a gaussian distribution
        _min: minimum value of sample after clip
        _max: maximum value of sample after clip
    Return:
        sample from the gaussian distribution after clip
        the log probability of sample
    """
    std = tf.exp(log_std)
    pi = mu + tf.random.normal(mu.shape) * std
    pi = tf.clip_by_value(pi, _min, _max)
    log_pi = gaussian_likelihood(pi, mu, log_std)
    return pi, log_pi


def gaussian_likelihood(x, mu, log_std):
    """
    Calculating the log probability of a sample from gaussian distribution.
    Args:
        x: sample data from Normal(mu, std)
        mu: mean of the gaussian distribution
        log_std: log standard deviation of the gaussian distribution
    Return:
        log probability of sample
    """
    pre_sum = -0.5 * (((x - mu) / (tf.exp(log_std) + 1e-8))**2 + 2 * log_std + np.log(2 * np.pi))
    return tf.reduce_sum(pre_sum, axis=1, keepdims=True)


def gaussian_entropy(log_std):
    '''
    Calculating the entropy of a Gaussian distribution.
    Args:
        log_std: log standard deviation of the gaussian distribution.
    Return:
        The average entropy of a batch of data.
    '''
    return tf.reduce_mean(0.5 * (1 + tf.math.log(2 * np.pi * tf.exp(log_std)**2 + 1e-8)))


def squash_action(pi, log_pi=None):
    """
    Enforcing action bounds.
    squash action to range [-1, 1] and calculate the correct log probability value.
    Args:
        pi: sample of gaussian distribution
        log_pi: log probability of the sample
    Return:
        sample range of [-1, 1] after squashed.
        the corrected log probability of squashed sample.
    """
    pi = tf.tanh(pi)
    if log_pi is not None:
        sub = tf.reduce_sum(tf.math.log(clip_but_pass_gradient(1 - pi**2, l=0, h=1) + 1e-8), axis=1, keepdims=True)
        log_pi -= sub
    return pi, log_pi


def clip_but_pass_gradient(x, l=-1., h=1.):
    """
    Stole this function from SpinningUp
    Args:
        x: data to be clipped.
        l: lower bound
        h: upper bound.
    Return:
        if x < l:
            l
        elif x > h:
            h
        else:
            x
    """
    clip_up = tf.cast(x > h, tf.float32)
    clip_low = tf.cast(x < l, tf.float32)
    return x + tf.stop_gradient((h - x) * clip_up + (l - x) * clip_low)


def squash_reprmter_action(mu, log_std):
    '''
    Reparameter sample from guassian distribution. Sqashing output from [-inf, inf] to [-1, 1]
    Args:
        mu: mean of guassian distribution
        log_std: log standard deviation of guassian distribution
    Return:
        actions range from [-1, 1], like [batch, action_value]
    '''
    return squash_action(*gaussian_reparam_sample(mu, log_std))