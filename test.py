millis = int(input("Gib die Millisekunden ein: "))
seconds = millis // 1000
minutes = seconds // 60
rest_seconds = seconds % 60
print(f"{minutes}:{rest_seconds:02d}")  # ergibt z.B. 0:17
