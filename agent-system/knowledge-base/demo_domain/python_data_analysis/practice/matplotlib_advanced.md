# Matplotlib 高级图表

## 子图布局

### subplot 方法

```python
import matplotlib.pyplot as plt
import numpy as np

fig, axes = plt.subplots(2, 2, figsize=(12, 10))

x = np.linspace(0, 10, 100)

axes[0, 0].plot(x, np.sin(x))
axes[0, 0].set_title('Sin(x)')

axes[0, 1].plot(x, np.cos(x), 'r-')
axes[0, 1].set_title('Cos(x)')

axes[1, 0].plot(x, np.tan(x), 'g-')
axes[1, 0].set_ylim(-5, 5)
axes[1, 0].set_title('Tan(x)')

axes[1, 1].plot(x, np.exp(-x), 'm-')
axes[1, 1].set_title('Exp(-x)')

plt.tight_layout()
plt.show()
```

### 不等分子图

```python
fig = plt.figure(figsize=(12, 6))

# 大图占左半边
ax1 = fig.add_subplot(1, 2, 1)
ax1.plot(x, np.sin(x))
ax1.set_title('Large Plot')

# 右半边分上下两个小图
ax2 = fig.add_subplot(2, 2, 2)
ax2.plot(x, np.cos(x))
ax2.set_title('Top Right')

ax3 = fig.add_subplot(2, 2, 4)
ax3.plot(x, np.tan(x))
ax3.set_ylim(-5, 5)
ax3.set_title('Bottom Right')

plt.tight_layout()
plt.show()
```

## 双轴图

```python
fig, ax1 = plt.subplots(figsize=(10, 6))

x = np.arange(0, 10, 0.1)
y1 = np.sin(x)
y2 = np.exp(x / 3)

ax1.plot(x, y1, 'b-', label='Sin(x)')
ax1.set_xlabel('X')
ax1.set_ylabel('Sin(x)', color='b')
ax1.tick_params(axis='y', labelcolor='b')

ax2 = ax1.twinx()
ax2.plot(x, y2, 'r-', label='Exp(x/3)')
ax2.set_ylabel('Exp(x/3)', color='r')
ax2.tick_params(axis='y', labelcolor='r')

fig.legend(loc='upper right', bbox_to_anchor=(0.9, 0.9))
plt.title('Dual Axis Chart')
plt.show()
```

## 热力图

```python
data = np.random.rand(10, 10)

fig, ax = plt.subplots(figsize=(8, 8))
im = ax.imshow(data, cmap='YlOrRd', interpolation='nearest')
plt.colorbar(im)

ax.set_xticks(range(10))
ax.set_yticks(range(10))
ax.set_title('Heatmap')
plt.show()
```

## 3D 图表

```python
from mpl_toolkits.mplot3d import Axes3D

fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

x = np.linspace(-5, 5, 50)
y = np.linspace(-5, 5, 50)
X, Y = np.meshgrid(x, y)
Z = np.sin(np.sqrt(X**2 + Y**2))

ax.plot_surface(X, Y, Z, cmap='viridis', alpha=0.8)
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
ax.set_title('3D Surface Plot')
plt.show()
```

## 动画

```python
from matplotlib.animation import FuncAnimation

fig, ax = plt.subplots()
x = np.linspace(0, 2*np.pi, 100)
line, = ax.plot(x, np.sin(x))

def update(frame):
    line.set_ydata(np.sin(x + frame / 10))
    return line,

ani = FuncAnimation(fig, update, frames=100, interval=50, blit=True)
ani.save('animation.gif', writer='pillow')
plt.show()
```

## 自定义样式

```python
# 使用内置样式
plt.style.use('seaborn-v0_8-darkgrid')

# 自定义 rcParams
plt.rcParams.update({
    'figure.figsize': (10, 6),
    'font.size': 12,
    'axes.titlesize': 16,
    'axes.labelsize': 14,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
    'legend.fontsize': 12,
    'figure.dpi': 100,
})

# 自定义颜色循环
colors = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6']
plt.rcParams['axes.prop_cycle'] = plt.cycler(color=colors)
```

## 注释和标注

```python
fig, ax = plt.subplots()
x = np.linspace(0, 10, 100)
y = np.sin(x)
ax.plot(x, y)

# 箭头注释
ax.annotate('Maximum', xy=(np.pi/2, 1), xytext=(2, 0.5),
            arrowprops=dict(facecolor='black', shrink=0.05),
            fontsize=12)

# 水平/垂直参考线
ax.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
ax.axvline(x=np.pi, color='red', linestyle='--', alpha=0.5)

plt.show()
```
