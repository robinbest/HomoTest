import numpy as np
import matplotlib.pyplot as plt
import csv
import sys


def read_csv_xy(filename):
    x = []
    y = []
    with open(filename, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            try:
                xi = float(row[0])
                yi = float(row[1])
                x.append(xi)
                y.append(yi)
            except ValueError:
                # skip header or bad rows
                continue
    return np.array(x), np.array(y)


def plot_curves(file1, file2, file3, label1="Curve 1", label2="Curve 2", label3="Curve 3"):
    x1, y1 = read_csv_xy(file1)
    x2, y2 = read_csv_xy(file2)
    x3, y3 = read_csv_xy(file3)

    plt.figure(figsize=(8, 6))

    # First curve: solid line
    plt.plot(x1, y1,
             linestyle='--',
             linewidth=2,
             label=label1)

    # Second curve: different color + marker
    plt.plot(x2, y2,
             linestyle='--',
             marker='o',
             markersize=4,
             linewidth=1,
             label=label2)

    plt.plot(x3, y3,
             linestyle='-',
             markersize=5,
             linewidth=1.5,
             label=label3)

    plt.xlabel("Ply angle (degrees)")
    plt.ylabel("Torsional rigidity (lb-in^2)")
    #plt.title("Curve Comparison")

    # 1. Set the x-axis range (0 to 90) [1]
    plt.xlim(0, 90)
    # 2. Set the tick frequency (0, 15, 30, ..., 90) [1, 9]
    plt.xticks(np.arange(0, 91, 15))

    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.show()


# python plot_compare.py angle_S44.csv angle_yu2002.csv
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python plot_compare.py file1.csv file2.csv")
        sys.exit(1)

    file1 = sys.argv[1]
    file2 = sys.argv[2]
    file3 = sys.argv[3]

    plot_curves(file1, file2, file3, "HomoGen linear", "HomoGen quadratic", "Analytical")