#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auth Service App Package
"""

# Facilitar imports
from .main import app
from .services import AuthService
from .schemas import *

__all__ = ['app', 'AuthService']