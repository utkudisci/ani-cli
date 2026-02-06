import flet as ft

# Check PubSub methods
print("PubSub methods:")
for attr in dir(ft.PubSubClient):
    if not attr.startswith('_'):
        print(f"  {attr}")

# Check unsubscribe signature
import inspect
print("\nUnsubscribe signature:")
print(inspect.signature(ft.PubSubClient.unsubscribe))
