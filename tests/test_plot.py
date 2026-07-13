import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import plot


class FakeAxis:
    def __init__(self):
        self.xlim = None
        self.ylim = None

    def scatter(self, *_args, **_kwargs):
        return None

    def set_xlim(self, left, right):
        self.xlim = (left, right)

    def set_ylim(self, bottom, top):
        self.ylim = (bottom, top)

    def set_aspect(self, *_args, **_kwargs):
        return None

    def set_xticks(self, *_args, **_kwargs):
        return None

    def set_yticks(self, *_args, **_kwargs):
        return None

    def tick_params(self, *_args, **_kwargs):
        return None

    def margins(self, *_args, **_kwargs):
        return None


class FakeFigure:
    def subplots_adjust(self, *_args, **_kwargs):
        return None


class PlotTests(unittest.TestCase):
    def test_make_plot_sets_bounds_and_saves_image(self):
        fake_axis = FakeAxis()
        fake_figure = FakeFigure()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_plot = Path(tmpdir) / "plot.jpeg"

            df = plot.pd.DataFrame(
                [
                    {"lat": 21.0, "lon": 105.0},
                    {"lat": 21.2, "lon": 105.3},
                    {"lat": 21.1, "lon": 105.1},
                ]
            )

            with mock.patch("scripts.plot.plt.subplots", return_value=(fake_figure, fake_axis)):
                with mock.patch("scripts.plot.ctx.add_basemap") as mock_basemap:
                    with mock.patch("scripts.plot.plt.title") as mock_title:
                        with mock.patch("scripts.plot.plt.savefig") as mock_save:
                            with mock.patch("scripts.plot.plt.close"):
                                plot.make_plot(df, "Trip", str(output_plot))

        self.assertEqual(fake_axis.xlim, (105.0, 105.3))
        self.assertEqual(fake_axis.ylim, (21.0, 21.2))
        mock_basemap.assert_called_once()
        mock_title.assert_called_once_with("Trip")
        mock_save.assert_called_once()

    def test_main_reads_csv_and_delegates_to_make_plot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_csv = Path(tmpdir) / "points.csv"
            output_plot = Path(tmpdir) / "plot.jpeg"
            input_csv.write_text("lat,lon\n21.0,105.0\n", encoding="utf-8")

            with mock.patch("scripts.plot.make_plot") as mock_make_plot:
                plot.main(str(input_csv), "Title", str(output_plot))

        mock_make_plot.assert_called_once()
        called_df = mock_make_plot.call_args.args[0]
        self.assertEqual(list(called_df.columns), ["lat", "lon"])
        self.assertEqual(len(called_df), 1)


if __name__ == "__main__":
    unittest.main()
