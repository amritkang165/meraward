"""Shared code for the MERAWARD Lambdas.

Kept dependency-light on purpose: everything in here must import cleanly on a
Lambda runtime without a layer, so the cold-start path stays boring.
"""
