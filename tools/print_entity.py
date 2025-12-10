import sys
import os
from pathlib import Path

# Ensure repo root is on sys.path so `backend` imports work when running this script directly
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.preservica_client import PreservicaClient
import json

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python tools/print_entity.py <asset_reference>")
        sys.exit(1)

    ref = sys.argv[1]
    client = PreservicaClient().client
    try:
        asset = client.asset(ref)
    except Exception:
        asset = client.folder(ref)

    # Print a compact diagnostic: dir() and a few attributes
    print("--- dir() (first 200) ---")
    attrs = [a for a in dir(asset) if not a.startswith('_')][:200]
    print(json.dumps(attrs, indent=2))

    print("\n--- attribute samples (name -> type -> repr) ---")
    for name in attrs:
        try:
            val = getattr(asset, name)
        except Exception:
            val = '<error>'
        t = type(val).__name__
        try:
            r = repr(val)
        except Exception:
            r = '<repr error>'
        # truncate long reprs
        if len(r) > 1000:
            r = r[:1000] + '...'
        print(f"{name} => {t} => {r}\n")

    # Probe common client methods that might return representations/renditions
    probe_methods = [
        'representations', 'get_representations', 'representation', 'get_representation',
        'get_representations_for', 'representations_for', 'get_asset_representations', 'asset_representations',
        'get_representations_for_asset', 'get_representation_for'
    ]

    print('\n--- probing client for representation methods ---')
    for m in probe_methods:
        meth = getattr(client, m, None)
        if not callable(meth):
            print(f"{m}: not available")
            continue
        try:
            # try common calling patterns
            try:
                res = meth(ref)
            except TypeError:
                try:
                    res = meth(asset)
                except TypeError:
                    try:
                        res = meth()
                    except Exception as e:
                        res = f"call failed: {e}"
            print(f"{m} => type: {type(res).__name__}")
            # print a short representation if it's printable
            try:
                rep = repr(res)
                if len(rep) > 1000:
                    rep = rep[:1000] + '...'
                print(rep)
            except Exception:
                pass
        except Exception as e:
            print(f"{m} => call raised: {e}")

    print("\nDone.")

    # Print client introspection to help locate methods
    print('\n--- client dir (first 300) ---')
    try:
        client_attrs = [a for a in dir(client) if not a.startswith('_')][:300]
        print(json.dumps(client_attrs, indent=2))
    except Exception as e:
        print('Could not list client attributes:', e)

    # Explicitly call common thumbnail/bitstream methods to surface their return values
    print('\n--- explicit thumbnail/bitstream probes ---')
    try:
        if hasattr(client, 'has_thumbnail') and callable(client.has_thumbnail):
            try:
                print('has_thumbnail(ref) =>', client.has_thumbnail(ref))
            except Exception as e:
                print('has_thumbnail(ref) raised:', e)
        if hasattr(client, 'thumbnail') and callable(client.thumbnail):
            try:
                t = client.thumbnail(ref)
                print('thumbnail(ref) => type:', type(t).__name__)
                rep = repr(t)
                if len(rep) > 1000:
                    rep = rep[:1000] + '...'
                print(rep)
            except Exception as e:
                print('thumbnail(ref) raised:', e)
        if hasattr(client, 'bitstreams_for_asset') and callable(client.bitstreams_for_asset):
            try:
                b = client.bitstreams_for_asset(ref)
                print('bitstreams_for_asset(ref) => type:', type(b).__name__)
                rep = repr(b)
                if len(rep) > 1000:
                    rep = rep[:1000] + '...'
                print(rep)
            except Exception as e:
                print('bitstreams_for_asset(ref) raised:', e)
        if hasattr(client, 'bitstream_bytes') and callable(client.bitstream_bytes):
            print('bitstream_bytes method available (requires id)')
        if hasattr(client, 'download') and callable(client.download):
            try:
                d = client.download(ref)
                print('download(ref) => type:', type(d).__name__)
                rep = repr(d)
                if len(rep) > 1000:
                    rep = rep[:1000] + '...'
                print(rep)
            except Exception as e:
                print('download(ref) raised:', e)
    except Exception as e:
        print('Error probing thumbnail/bitstream methods:', e)
