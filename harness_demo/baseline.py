def optimize(start, steps):
    x, y = start
    for _ in range(steps):
        x -= 0.001 * 2 * (x - 1)
        y -= 0.001 * 200 * (y + 2)
    return x, y
