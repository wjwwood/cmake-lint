#!/usr/bin/env python
"""
Copyright 2009 Richard Quirk

Licensed under the Apache License, Version 2.0 (the "License"); you may not
use this file except in compliance with the License. You may obtain a copy of
the License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations under
the License.
"""
import unittest
import cmakelint.main
import cmakelint.__version__
import os

class ErrorCollector(object):
    def __init__(self):
        self._errors = []

    def __call__(self, unused_filename, unused_line, category, message):
        self._errors.append(message)

    def Results(self):
        if len(self._errors) < 2:
            return ''.join(self._errors)
        return self._errors

class CMakeLintTestBase(unittest.TestCase):
    def doTestLint(self, code, expected_message):
        errors = ErrorCollector()
        clean_lines = cmakelint.main.CleansedLines([code])
        cmakelint.main.ProcessLine('foo.cmake', 0, clean_lines, errors)
        self.assertEquals(expected_message, errors.Results())

    def doTestMultiLineLint(self, code, expected_message):
        errors = ErrorCollector()
        clean_lines = cmakelint.main.CleansedLines(code.split('\n'))
        for i in clean_lines.LineNumbers():
            cmakelint.main.ProcessLine('foo.cmake', i, clean_lines, errors)
        self.assertEquals(expected_message, errors.Results())

    def doTestCheckRepeatLogic(self, code, expected_message):
        errors = ErrorCollector()
        clean_lines = cmakelint.main.CleansedLines(code.split('\n'))
        for i in clean_lines.LineNumbers():
            cmakelint.main.CheckRepeatLogic('foo.cmake', i, clean_lines, errors)
        self.assertEquals(expected_message, errors.Results())

    def doTestCheckFileName(self, filename, expected_message):
        errors = ErrorCollector()
        cmakelint.main.CheckFileName(filename, errors)
        self.assertEquals(expected_message, errors.Results())

    def doTestCheckFindPackage(self, filename, code, expected_message):
        errors = ErrorCollector()
        clean_lines = cmakelint.main.CleansedLines(code.split('\n'))
        for i in clean_lines.LineNumbers():
            cmakelint.main.CheckFindPackage(filename, i, clean_lines, errors)
        cmakelint.main._package_state.Done(filename, errors)
        self.assertEquals(expected_message, errors.Results())

    def doTestGetArgument(self, expected_arg, code):
        clean_lines = cmakelint.main.CleansedLines(code.split('\n'))
        self.assertEquals(expected_arg, cmakelint.main.GetCommandArgument(0, clean_lines))

class CMakeLintTest(CMakeLintTestBase):
    def testLineLength(self):
        self.doTestLint(
                '# '+('o'*80),
                'Lines should be <= 80 characters long')

    def testUpperAndLowerCase(self):
        self.doTestMultiLineLint(
                '''project()
                CMAKE_MINIMUM_REQUIRED()''',
                'Do not mix upper and lower case commands')

    def testContainsCommand(self):
        self.assertTrue(cmakelint.main.ContainsCommand('project()'))
        self.assertTrue(cmakelint.main.ContainsCommand('project('))
        self.assertTrue(cmakelint.main.ContainsCommand('project  ( '))
        self.assertFalse(cmakelint.main.ContainsCommand('VERSION'))

    def testGetCommand(self):
        self.assertEquals('project', cmakelint.main.GetCommand('project()'))
        self.assertEquals('project', cmakelint.main.GetCommand('project('))
        self.assertEquals('project', cmakelint.main.GetCommand('project  ( '))
        self.assertEquals('', cmakelint.main.GetCommand('VERSION'))

    def testIsCommandUpperCase(self):
        self.assertTrue(cmakelint.main.IsCommandUpperCase('PROJECT'))
        self.assertTrue(cmakelint.main.IsCommandUpperCase('CMAKE_MINIMUM_REQUIRED'))
        self.assertFalse(cmakelint.main.IsCommandUpperCase('cmake_minimum_required'))
        self.assertFalse(cmakelint.main.IsCommandUpperCase('project'))
        self.assertFalse(cmakelint.main.IsCommandUpperCase('PrOjEct'))

    def testIsCommandMixedCase(self):
        self.assertTrue(cmakelint.main.IsCommandMixedCase('PrOjEct'))
        self.assertFalse(cmakelint.main.IsCommandMixedCase('project'))
        self.assertFalse(cmakelint.main.IsCommandMixedCase('CMAKE_MINIMUM_REQUIRED'))
        self.assertTrue(cmakelint.main.IsCommandMixedCase('CMAKE_MINIMUM_required'))

    def testCleanComment(self):
        self.assertEquals('', cmakelint.main.CleanComments('# Comment to zap'))
        self.assertEquals(
                'project()',
                cmakelint.main.CleanComments('project() # Comment to zap'))

    def testCommandSpaces(self):
        self.doTestMultiLineLint(
                """project ()""",
                "Extra spaces between 'project' and its ()")

    def testTabs(self):
        self.doTestLint('\tfoo()', 'Tab found; please use spaces')

    def testTrailingSpaces(self):
        self.doTestLint('# test ', 'Line ends in whitespace')
        self.doTestMultiLineLint('  foo() \n  foo()\n', 'Line ends in whitespace')
        self.doTestLint('    set(var value)', '')

    def testCommandSpaceBalance(self):
        self.doTestMultiLineLint(
                """project( Foo)""",
                'Mismatching spaces inside () after command')
        self.doTestMultiLineLint(
                """project(Foo )""",
                'Mismatching spaces inside () after command')

    def testCommandNotEnded(self):
        self.doTestMultiLineLint(
                """project(
                Foo
                #
                #""",
                'Unable to find the end of this command')

    def testRepeatLogicExpression(self):
        self.doTestCheckRepeatLogic('else(foo)',
                'Expression repeated inside else; '
                'better to use only else()')
        self.doTestCheckRepeatLogic('ELSEIF(NOT ${VAR})', '')
        self.doTestCheckRepeatLogic('ENDMACRO( my_macro foo bar baz)',
                'Expression repeated inside endmacro; '
                'better to use only ENDMACRO()')

    def testFindTool(self):
        self.doTestCheckFileName('path/to/FindFooBar.cmake',
                'Find modules should use uppercase names; '
                'consider using FindFOOBAR.cmake')
        self.doTestCheckFileName('CMakeLists.txt', '')
        self.doTestCheckFileName('cmakeLists.txt',
                    'File should be called CMakeLists.txt')

    def testIsFindPackage(self):
        self.assertTrue(cmakelint.main.IsFindPackage('path/to/FindFOO.cmake'))
        self.assertFalse(cmakelint.main.IsFindPackage('path/to/FeatureFOO.cmake'))

    def testCheckFindPackage(self):
        self.doTestCheckFindPackage(
                'FindFoo.cmake',
                '',
                ['Package should include FindPackageHandleStandardArgs',
                'Package should use FIND_PACKAGE_HANDLE_STANDARD_ARGS'])
        self.doTestCheckFindPackage(
                'FindFoo.cmake',
                '''INCLUDE(FindPackageHandleStandardArgs)''',
                'Package should use FIND_PACKAGE_HANDLE_STANDARD_ARGS')
        self.doTestCheckFindPackage(
                'FindFoo.cmake',
                '''FIND_PACKAGE_HANDLE_STANDARD_ARGS(FOO DEFAULT_MSG)''',
                'Package should include FindPackageHandleStandardArgs')
        self.doTestCheckFindPackage(
                'FindFoo.cmake',
                '''INCLUDE(FindPackageHandleStandardArgs)
                FIND_PACKAGE_HANDLE_STANDARD_ARGS(KK DEFAULT_MSG)''',
                'Weird variable passed to std args, should be FOO not KK')
        self.doTestCheckFindPackage(
                'FindFoo.cmake',
                '''INCLUDE(FindPackageHandleStandardArgs)
                FIND_PACKAGE_HANDLE_STANDARD_ARGS(FOO DEFAULT_MSG)''',
                '')

    def testGetCommandArgument(self):
        self.doTestGetArgument('KK',
                '''SET(
                KK)''')
        self.doTestGetArgument('KK', 'Set(  KK)')
        self.doTestGetArgument('KK', 'FIND_PACKAGE_HANDLE_STANDARD_ARGS(KK BLEUGH)')

    def testIsValidFile(self):
        self.assertTrue(cmakelint.main.IsValidFile('CMakeLists.txt'))
        self.assertTrue(cmakelint.main.IsValidFile('cmakelists.txt'))
        self.assertTrue(cmakelint.main.IsValidFile('/foo/bar/baz/CMakeLists.txt'))
        self.assertTrue(cmakelint.main.IsValidFile('Findkk.cmake'))
        self.assertFalse(cmakelint.main.IsValidFile('foobar.h.in'))

    def testIndent(self):
        try:
            cmakelint.main._lint_state.spaces = 2
            self.doTestLint('no_indent(test)', '')
            self.doTestLint('  two_indent(test)', '')
            self.doTestLint('    four_indent(test)', '')
            self.doTestLint(' one_indent(test)',
                    'Weird indentation; use 2 spaces')
            self.doTestLint('   three_indent(test)',
                    'Weird indentation; use 2 spaces')

            cmakelint.main._lint_state.spaces = 3
            self.doTestLint('no_indent(test)', '')
            self.doTestLint('  two_indent(test)',
                    'Weird indentation; use 3 spaces')
            self.doTestLint('    four_indent(test)',
                    'Weird indentation; use 3 spaces')
            self.doTestLint(' one_indent(test)',
                    'Weird indentation; use 3 spaces')
            self.doTestLint('   three_indent(test)', '')
        finally:
            cmakelint.main._lint_state.spaces = 2

    def testParseArgs(self):
        old_usage = cmakelint.main._USAGE
        old_version = cmakelint.__version__.VERSION
        old_cats = cmakelint.main._ERROR_CATEGORIES
        old_spaces = cmakelint.main._lint_state.spaces
        try:
            cmakelint.main._USAGE = ""
            cmakelint.main._ERROR_CATEGORIES = ""
            cmakelint.main._VERSION = ""
            self.assertRaises(SystemExit, cmakelint.main.ParseArgs, [])
            self.assertRaises(SystemExit, cmakelint.main.ParseArgs, ['--help'])
            self.assertRaises(SystemExit, cmakelint.main.ParseArgs, ['--bogus-option'])
            self.assertRaises(SystemExit, cmakelint.main.ParseArgs, ['--filter='])
            self.assertRaises(SystemExit, cmakelint.main.ParseArgs, ['--filter=foo'])
            self.assertRaises(SystemExit, cmakelint.main.ParseArgs, ['--filter=+x,b,-c', 'foo.cmake'])
            self.assertRaises(SystemExit, cmakelint.main.ParseArgs, ['--spaces=c', 'foo.cmake'])
            self.assertRaises(SystemExit, cmakelint.main.ParseArgs, ['--version'])
            cmakelint.main._lint_state.filters = []
            self.assertEquals(['foo.cmake'], cmakelint.main.ParseArgs(['--filter=-whitespace', 'foo.cmake']))
            cmakelint.main._lint_state.filters = []
            self.assertEquals(['foo.cmake'], cmakelint.main.ParseArgs(['foo.cmake']))
            filt = '-,+whitespace'
            cmakelint.main._lint_state.filters = []
            self.assertEquals(['foo.cmake'], cmakelint.main.ParseArgs(['--config=None', '--spaces=3', '--filter='+filt, 'foo.cmake']))
            self.assertEquals(['-', '+whitespace'], cmakelint.main._lint_state.filters)
            self.assertEquals(3, cmakelint.main._lint_state.spaces)
            cmakelint.main._lint_state.filters = []

            cmakelint.main.ParseArgs(['--config=./foo/bar', 'foo.cmake'])
            self.assertEquals('./foo/bar', cmakelint.main._lint_state.config)
            cmakelint.main.ParseArgs(['--config=None', 'foo.cmake'])
            self.assertEquals(None, cmakelint.main._lint_state.config)
            cmakelint.main.ParseArgs(['foo.cmake'])
            self.assertEquals(os.environ['HOME']+os.path.sep+'.cmakelintrc', cmakelint.main._lint_state.config)

        finally:
            cmakelint.main._USAGE = old_usage
            cmakelint.main._ERROR_CATEGORIES = old_cats
            cmakelint.main._VERSION = old_version
            cmakelint.main._lint_state.filters = []
            cmakelint.main._lint_state.spaces = old_spaces

    def testParseOptionsFile(self):
        old_usage = cmakelint.main._USAGE
        old_cats = cmakelint.main._ERROR_CATEGORIES
        old_spaces = cmakelint.main._lint_state.spaces
        try:
            cmakelint.main._USAGE = ""
            cmakelint.main._ERROR_CATEGORIES = ""
            cmakelint.main.ParseOptionFile("""
                    # skip comment
                    filter=-,+whitespace
                    spaces= 3
                    """.split('\n'), ignore_space=False)
            self.assertEquals(['-', '+whitespace'], cmakelint.main._lint_state.filters)
            cmakelint.main.ParseArgs(['--filter=+syntax','foo.cmake'])
            self.assertEquals(['-', '+whitespace', '+syntax'], cmakelint.main._lint_state.filters)
            self.assertEquals(3, cmakelint.main._lint_state.spaces)

            cmakelint.main._lint_state.spaces = 2
            cmakelint.main.ParseOptionFile("""
                    # skip comment
                    spaces= 4
                    """.split('\n'), ignore_space=True)
            self.assertEquals(2, cmakelint.main._lint_state.spaces)

            cmakelint.main.ParseOptionFile("""
                    # skip comment
                    """.split('\n'), ignore_space=False)
            self.assertEquals(2, cmakelint.main._lint_state.spaces)
        finally:
            cmakelint.main._USAGE = old_usage
            cmakelint.main._ERROR_CATEGORIES = old_cats
            cmakelint.main._lint_state.spaces = old_spaces

if __name__ == '__main__':
    unittest.main()
