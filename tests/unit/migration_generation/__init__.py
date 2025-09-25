"""Unit tests for migration file generation with default values

This module contains comprehensive tests for the generate_crud.py script's
migration file generation, specifically focusing on the bug that was fixed
where default values were placed outside the sa.Column() function call.
"""
