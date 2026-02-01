#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auth Service Package
"""

from .app.main import app
from .app.services import AuthService

__all__ = ['app', 'AuthService']