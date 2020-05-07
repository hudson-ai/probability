# Copyright 2020 The TensorFlow Probability Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""GeneralizedExtremeValue bijector."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow.compat.v2 as tf

from tensorflow_probability.python.bijectors import bijector
from tensorflow_probability.python.internal import assert_util
from tensorflow_probability.python.internal import dtype_util
from tensorflow_probability.python.internal import tensor_util


__all__ = [
    'GeneralizedExtremeValueCDF',
]


class GeneralizedExtremeValueCDF(bijector.Bijector):
  """Compute `Y = g(X) = exp(-t(X))`, the GeneralizedExtremeValue CDF,
  where `t(x)` is defined to be:
    *`(1 + conc * (x - loc) / scale) ) ** (-1 / conc)` when `conc != 0`;
    *`exp(-(x - loc) / scale)` when `conc = 0`.

  This bijector maps inputs from the domain to `[0, 1]`, where the domain is
    * [loc - scale/conc, inf) when conc > 0;
    * (-inf, loc - scale/conc] when conc < 0;
    * (-inf, inf) when conc = 0;

  The inverse of the bijector applied to a uniform random variable
  `X ~ U(0, 1)` gives back a random variable with the
  [Generalized extreme value distribution](
  https://https://en.wikipedia.org/wiki/Generalized_extreme_value_distribution):

  ```none
  Y ~ GeneralizedExtremeValueCDF(loc, scale, conc)
  pdf(y; loc, scale, conc) = t(y; loc, scale, conc) ** (1 + conc) * exp(
  - t(y; loc, scale, conc) ) / scale
  where t(x) =
    * (1 + conc * (x - loc) / scale) ) ** (-1 / conc) when conc != 0;
    * exp(-(x - loc) / scale) when conc = 0.
  ```
  """

  def __init__(self,
               loc=0.,
               scale=1.,
               concentration=0,
               validate_args=False,
               tol=1e-5,
               name='generalizedextremevalue_cdf'):
    """Instantiates the `GeneralizedExtremeValueCDF` bijector.

    Args:
      loc: Float-like `Tensor` that is the same dtype and is
        broadcastable with `scale` and `concentration`.
      scale: Positive Float-like `Tensor` that is the same dtype and is
        broadcastable with `loc` and `concentration`.
      concentration: Nonzero float-like `Tensor` that is the same dtype and is
        broadcastable with `loc` and `scale`.
      validate_args: Python `bool` indicating whether arguments should be
        checked for correctness.
      name: Python `str` name given to ops managed by this object.
    """
    parameters = dict(locals())
    with tf.name_scope(name) as name:
      dtype = dtype_util.common_dtype(
          [loc, scale, concentration], dtype_hint=tf.float32)
      self._loc = tensor_util.convert_nonref_to_tensor(
          loc, dtype=dtype, name='loc')
      self._scale = tensor_util.convert_nonref_to_tensor(
          scale, dtype=dtype, name='scale')
      self._concentration = tensor_util.convert_nonref_to_tensor(
          concentration, dtype=dtype, name='concentration')
      self._tol = tensor_util.convert_nonref_to_tensor(
          tol, dtype=dtype, name='concentration')
      super(GeneralizedExtremeValueCDF, self).__init__(
          validate_args=validate_args,
          forward_min_event_ndims=0,
          parameters=parameters,
          name=name)

  @property
  def loc(self):
    """
    The `loc` in `Y = exp(-t(X))`
    where `t(x) = (1 + conc * (x - loc) / scale) ) ** (-1 / conc)`
    when `conc != 0` and `exp(-(x - loc) / scale)` when `conc = 0`.`
    """
    return self._loc

  @property
  def scale(self):
    """
    The `scale` in `Y = exp(-t(X))`
    where `t(x) = (1 + conc * (x - loc) / scale) ) ** (-1 / conc)`
    when `conc != 0` and `exp(-(x - loc) / scale)` when `conc = 0`.`
    """
    return self._scale

  @property
  def concentration(self):
    """
    The `concentration` in `Y = exp(-t(X))`
    where `t(x) = (1 + conc * (x - loc) / scale) ) ** (-1 / conc)`
    when `conc != 0` and `exp(-(x - loc) / scale)` when `conc = 0`.`
    """
    return self._concentration

  @classmethod
  def _is_increasing(cls):
    return True

  def _forward(self, x):
    with tf.control_dependencies(self._maybe_assert_valid_x(x)):
      conc = tf.convert_to_tensor(self.concentration)

      z = (x - self.loc) / self.scale
      t = tf.where(tf.math.less_equal(tf.math.abs(conc), self._tol),
                   tf.exp(-z),
                   tf.exp(-tf.math.log1p(z * conc) / conc))
      return tf.exp(-t)

  def _inverse(self, y):
    with tf.control_dependencies(self._maybe_assert_valid_y(y)):
      t = -tf.math.log(y)

      conc = tf.convert_to_tensor(self.concentration)
      z = tf.where(tf.math.less_equal(tf.math.abs(conc), self._tol),
                   -tf.math.log(t),
                   tf.math.expm1(-tf.math.log(t) * conc) / conc)

      return self.loc + self.scale * z

  def _inverse_log_det_jacobian(self, y):
    with tf.control_dependencies(self._maybe_assert_valid_y(y)):
      t = -tf.math.log(y)

      conc = tf.convert_to_tensor(self.concentration)
      log_dt = (-conc - 1.) * tf.math.log(t)

      return tf.math.log(self.scale / y) + log_dt

  def _forward_log_det_jacobian(self, x):
    with tf.control_dependencies(self._maybe_assert_valid_x(x)):
      scale = tf.convert_to_tensor(self.scale)
      z = (x - self.loc) / scale

      conc = tf.convert_to_tensor(self.concentration)
      log_t = tf.where(tf.math.less_equal(tf.math.abs(conc), self._tol),
                       -z,
                       -tf.math.log1p(z * conc) / conc)

      return (conc + 1) * log_t - tf.exp(log_t) - tf.math.log(scale)

  def _maybe_assert_valid_x(self, x):
    if not self.validate_args:
      return []
    return [assert_util.assert_less_equal(
        self.concentration * self.loc - self.scale,
        x * self.concentration,
        message='Forward transformation input must be inside domain.')]

  def _maybe_assert_valid_y(self, y):
    if not self.validate_args:
      return []
    is_positive = assert_util.assert_non_negative(
        y, message='Inverse transformation input must be greater than 0.')
    less_than_one = assert_util.assert_less_equal(
        y,
        tf.constant(1., y.dtype),
        message='Inverse transformation input must be less than or equal to 1.')
    return [is_positive, less_than_one]

  def _parameter_control_dependencies(self, is_init):
    if not self.validate_args:
      return []
    assertions = []
    if is_init != tensor_util.is_ref(self.scale):
      assertions.append(assert_util.assert_positive(
          self.scale,
          message='Argument `scale` must be positive.'))
    return assertions
