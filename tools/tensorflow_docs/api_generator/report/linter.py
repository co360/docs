# Lint as: python3
# Copyright 2020 The TensorFlow Authors. All Rights Reserved.
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
# ==============================================================================
"""Lints the docstring of an API symbol."""

import ast
import inspect
import textwrap

from typing import Optional, Any

import astor

from tensorflow_docs.api_generator import parser
from tensorflow_docs.api_generator.report.schema import api_report_generated_pb2 as api_report_pb2


def _get_source(py_object: Any) -> Optional[str]:
  if py_object is not None:
    try:
      source = textwrap.dedent(inspect.getsource(py_object))
      return source
    except Exception:  # pylint: disable=broad-except
      return None
  return None


def lint_params():
  pass


def lint_description():
  pass


def lint_usage_example():
  pass


def lint_returns(
    page_info: parser.PageInfo) -> Optional[api_report_pb2.ReturnLint]:
  """"Lints the returns block in the docstring.

  This linter only checks if a `Returns` block exists in the docstring
  if it finds `return` keyword in the source code.

  Args:
    page_info: A `PageInfo` object containing the information of a page
      generated via the api generation.

  Returns:
    A filled `ReturnLint` proto object.
  """
  source = _get_source(page_info.py_object)
  if source is not None and 'return' in source:
    for item in page_info.doc.docstring_parts:
      if isinstance(item, parser.TitleBlock):
        if item.title.lower().startswith('return'):
          return api_report_pb2.ReturnLint(returns_defined=True)
    return api_report_pb2.ReturnLint(returns_defined=False)
  return None


class RaiseVisitor(ast.NodeVisitor):
  """Visits the Raises node in an AST."""

  def __init__(self) -> None:
    self.total_raises = []

  def visit_Raise(self, node) -> None:  # pylint: disable=invalid-name
    # This `if` block means that there is a bare raise in the code.
    if node.exc is None:
      return
    self.total_raises.append(astor.to_source(node.exc.func).strip())


def lint_raises(page_info: parser.PageInfo) -> api_report_pb2.RaisesLint:
  """Lints the raises block in the docstring.

  The total raises in code are extracted via an AST and compared against those
  extracted from the docstring.

  Args:
    page_info: A `PageInfo` object containing the information of a page
      generated via the api generation.

  Returns:
    A filled `RaisesLint` proto object.
  """

  raises_lint = api_report_pb2.RaisesLint()

  # Extract the raises from the source code.
  raise_visitor = RaiseVisitor()
  source = _get_source(page_info.py_object)
  if source is not None:
    try:
      raise_visitor.visit(ast.parse(source))
    except Exception:  # pylint: disable=broad-except
      pass
  raises_lint.total_raises_in_code = len(raise_visitor.total_raises)

  # Extract the raises defined in the docstring.
  raises_defined_in_doc = []
  for part in page_info.doc.docstring_parts:
    if isinstance(part, parser.TitleBlock):
      if part.title.lower().startswith('raises'):
        raises_lint.num_raises_defined = len(part.items)
        if part.items:
          raises_defined_in_doc.extend(list(zip(*part.items))[0])
        break
  else:
    raises_lint.num_raises_defined = 0

  # Raises mismatch is when the raises found in code don't match the raises
  # defined in the docstring.
  mismatch = set(raises_defined_in_doc) - set(raise_visitor.total_raises)
  raises_lint.num_raises_mismatch = len(mismatch)

  return raises_lint
