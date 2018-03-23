# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Trains and exports a simple linear regressor.

The true model is age * 3 + (language == 'english')

The model has the standard metrics added by LinearRegressor, plus additional
metrics added using tf.contrib.estimator.

This model also extracts an additional slice_key feature for evaluation
(this feature is not used in training).
"""
from __future__ import absolute_import
from __future__ import division

from __future__ import print_function



import tensorflow as tf
from tensorflow_model_analysis.eval_saved_model import export


def simple_linear_regressor(export_path, eval_export_path):
  """Trains and exports a simple linear regressor."""

  def eval_input_receiver_fn():
    """Eval input receiver function."""
    serialized_tf_example = tf.placeholder(
        dtype=tf.string, shape=[None], name='input_example_tensor')

    language = tf.contrib.layers.sparse_column_with_keys(
        'language', ['english', 'chinese'])
    slice_key = tf.contrib.layers.sparse_column_with_hash_bucket(
        'slice_key', 100)
    age = tf.contrib.layers.real_valued_column('age')
    label = tf.contrib.layers.real_valued_column('label')
    all_features = [age, language, label, slice_key]
    feature_spec = tf.contrib.layers.create_feature_spec_for_parsing(
        all_features)
    receiver_tensors = {'examples': serialized_tf_example}
    features = tf.parse_example(serialized_tf_example, feature_spec)

    return export.EvalInputReceiver(
        features=features,
        receiver_tensors=receiver_tensors,
        labels=features['label'])

  def input_fn():
    """Train input function."""
    return {
        'age':
            tf.constant([[1], [2], [3], [4], [1], [2], [3], [4], [10], [20],
                         [30], [40], [10], [20], [30], [40]]),
        'language':
            tf.SparseTensor(
                values=[
                    'english', 'english', 'english', 'english', 'chinese',
                    'chinese', 'chinese', 'chinese', 'english', 'english',
                    'english', 'english', 'chinese', 'chinese', 'chinese',
                    'chinese'
                ],
                indices=[[0, 0], [1, 0], [2, 0], [3, 0], [4, 0], [5, 0], [6, 0],
                         [7, 0], [8, 0], [9, 0], [10, 0], [11, 0], [12, 0],
                         [13, 0], [14, 0], [15, 0]],
                dense_shape=[16, 1])
    }, tf.constant([[4], [7], [10], [13], [3], [6], [9], [12], [31], [61], [91],
                    [121], [30], [60], [90], [120]])

  language = tf.contrib.layers.sparse_column_with_keys('language',
                                                       ['english', 'chinese'])
  age = tf.contrib.layers.real_valued_column('age')
  all_features = [age, language]  # slice_key not used in training.
  feature_spec = tf.contrib.layers.create_feature_spec_for_parsing(all_features)

  def my_metrics(features, labels, predictions):
    return {
        'my_mean_prediction': tf.metrics.mean(predictions['predictions']),
        'my_mean_age': tf.metrics.mean(features['age']),
        'my_mean_label': tf.metrics.mean(labels),
        'my_mean_age_times_label': tf.metrics.mean(labels * features['age']),
    }

  regressor = tf.estimator.LinearRegressor(feature_columns=all_features)
  regressor = tf.contrib.estimator.add_metrics(regressor, my_metrics)
  regressor.train(input_fn=input_fn, steps=3000)

  export_dir = None
  eval_export_dir = None
  if export_path:
    export_dir = regressor.export_savedmodel(
        export_dir_base=export_path,
        serving_input_receiver_fn=tf.estimator.export.
        build_parsing_serving_input_receiver_fn(feature_spec))

  if eval_export_path:
    eval_export_dir = export.export_eval_savedmodel(
        estimator=regressor,
        export_dir_base=eval_export_path,
        eval_input_receiver_fn=eval_input_receiver_fn)

  return export_dir, eval_export_dir
