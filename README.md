# peak-raid-results

This small project automatically downloads separate results from the [Peak Raid Maprun series](http://explorerevents.co.uk/map-run/) and combines points and time scores for each competitor. It then ranks competitors by overall number of points and time taken.

## Usage
In a virtual environment run the following, with year argument as desired:
```
pip install -r requirements.txt
python results.py --year 2023
```
This will produce year.csv and year.html files locally, which will also be uploaded to [http://qdata.byethost4.com/peakraid/](http://qdata.byethost4.com/peakraid/).

2023 combined results are available here:
- [HTML](http://qdata.byethost4.com/peakraid/2023.html)
- [CSV](http://qdata.byethost4.com/peakraid/2023.csv)

This script runs daily on a Raspberry Pi so the results stay up to date automatically.
