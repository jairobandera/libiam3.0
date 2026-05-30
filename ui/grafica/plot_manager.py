import pyqtgraph as pg


def limpiar(graphics):
    graphics.clear()


def crear_plots(graphics, señales_visibles):

    plots = {}

    row = 0
    primer_plot = None

    for categoria, señales in señales_visibles.items():

        if not señales:
            continue

        plot = graphics.addPlot(
            row=row,
            col=0,
            title=categoria
        )

        plot.setMinimumHeight(200)
        plot.setMouseEnabled(x=False, y=False)

        plot.showGrid(x=True, y=True, alpha=0.3)
        plot.addLegend()

        plot.setLabel("left", categoria)

        if primer_plot is None:
            primer_plot = plot
        else:
            plot.setXLink(primer_plot)

        plot.setLabel("bottom", "Tiempo (s)")

        plots[categoria] = plot
        row += 1

    # altura dinámica
    altura_por_plot = 250
    graphics.setMinimumHeight(row * altura_por_plot)

    return plots