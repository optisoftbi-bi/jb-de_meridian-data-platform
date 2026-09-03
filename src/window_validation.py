
def validate_month_window(name) -> bool:
    if len(name) != 7:
        return False

    
    
    if name == range(1, 12):
        return False
   