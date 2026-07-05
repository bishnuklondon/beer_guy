import { useEffect, useMemo, useRef, useState } from 'react';

const API_BASE = '/api';

function App() {
  const [allDistricts, setAllDistricts] = useState([]);
  const [counties, setCounties] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [selectedCounty, setSelectedCounty] = useState('');
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [pubs, setPubs] = useState([]);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('Loading counties...');
  const districtRequestId = useRef(0);
  const pubsRequestId = useRef(0);

  useEffect(() => {
    fetch(`${API_BASE}/districts`)
      .then((response) => response.json())
      .then((data) => {
        const districtList = data || [];
        const countyList = Array.from(new Set(districtList.map((district) => district.county_name).filter(Boolean))).sort();
        setAllDistricts(districtList);
        setCounties(countyList);
        if (countyList.length) {
          setSelectedCounty((currentCounty) => currentCounty || countyList[0]);
        }
        setStatus('Counties ready');
      })
      .catch(() => setStatus('Could not load counties yet. Start the backend first.'));
  }, []);

  useEffect(() => {
    if (!selectedCounty) {
      setDistricts([]);
      setSelectedDistrict('');
      return;
    }

    const requestId = ++districtRequestId.current;
    setStatus(`Loading districts for ${selectedCounty}...`);
    setPubs([]);

    fetch(`${API_BASE}/districts?county=${encodeURIComponent(selectedCounty)}`)
      .then((response) => response.json())
      .then((data) => {
        if (requestId !== districtRequestId.current) {
          return;
        }

        const countyDistricts = (data || []).filter((district) => district.county_name === selectedCounty);
        setDistricts(countyDistricts);
        if (!countyDistricts.length) {
          setSelectedDistrict('');
          setStatus(`No districts found for ${selectedCounty}`);
          return;
        }

        setSelectedDistrict((currentDistrict) => {
          if (currentDistrict && countyDistricts.some((district) => district.district_post_code === currentDistrict)) {
            return currentDistrict;
          }
          return countyDistricts[0].district_name;
        });
        setStatus(`Loaded ${countyDistricts.length} districts for ${selectedCounty}`);
      })
      .catch(() => {
        if (requestId === districtRequestId.current) {
          setStatus('Could not load districts for the selected county.');
        }
      });
  }, [selectedCounty]);

  useEffect(() => {
    if (!selectedDistrict) {
      setPubs([]);
      setStatus('Select a county and district to view pubs');
      return;
    }

    const requestId = ++pubsRequestId.current;
    const selectedDistrictData = districts.find((district) => district.district_name === selectedDistrict);
    const countyLabel = selectedDistrictData?.county_name || selectedCounty || 'your selection';
    setStatus(`Loading pubs for ${selectedDistrict} in ${countyLabel}...`);

    fetch(`${API_BASE}/pubs?district_name=${encodeURIComponent(selectedDistrict)}`)
      .then((response) => response.json())
      .then((data) => {
        if (requestId !== pubsRequestId.current) {
          return;
        }
        setPubs(data || []);
        setStatus(`Showing ${data?.length || 0} pubs for ${selectedDistrict}`);
        
      })
      .catch(() => {
        if (requestId === pubsRequestId.current) {
          setStatus('Could not load pubs.');
        }
      });      
          
  }, [selectedDistrict, selectedCounty, districts]);

  const filteredPubs = useMemo(() => {
          if (!search) {
            return pubs;
          }
          const needle = search.toLowerCase();
          return pubs.filter((pub) => JSON.stringify(pub).toLowerCase());
  }, [pubs, search]);
      
  const useMyLocation = async () => {
    try {
      const response = await fetch('https://ipapi.co/json/');
      const data = await response.json();
      if (data.postal) {
        const detectedDistrictCode = data.postal.slice(0, 3).toUpperCase();
        const detectedDistrict = allDistricts.find((district) => district.district_post_code === detectedDistrictCode);
        if (detectedDistrict) {
          setSelectedCounty(detectedDistrict.county_name);
          setSelectedDistrict(detectedDistrict.district_post_code);
          setStatus(`Detected ${detectedDistrict.district_post_code} in ${detectedDistrict.county_name}`);
        } else {
          setStatus(`Could not match your location postcode ${data.postal}`);
        }
      } else {
        setStatus('Location lookup did not return a postcode');
      }
    } catch {
      setStatus('Location lookup failed');
    }
  };

  return (
    <div className="app-shell">
      <header>
        <h1>Beer Guy</h1>
        <p>Find local pub offers, beers, wines and cocktails by county and district.</p>
      </header>

      <section className="controls">
        <label>
          County
          <select value={selectedCounty} onChange={(event) => setSelectedCounty(event.target.value)}>
            {counties.map((county) => (
              <option key={county} value={county}>
                {county}
              </option>
            ))}
          </select>
        </label>

        <label>
          District
          <select value={selectedDistrict} onChange={(event) => setSelectedDistrict(event.target.value)} disabled={!districts.length}>
            {districts.map((district) => (
              <option key={district.district_name} value={district.district_name}>
                {district.district_name}
              </option>
            ))}
          </select>
        </label>
        <label>
          ..
          <button onClick={useMyLocation}>Use my location</button>
        </label>
      </section>

      <section className="controls">
        <label>
          Search beverages
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="e.g. beer, wine, mojito" />
        </label>
      </section>

      <p className="status">{status}</p>

      <div className="card-grid">
        {filteredPubs.map((pub) => (
          <div className="card"> 
              <h2>{pub.name}</h2>
              <p>{pub.address}</p>
              <p>Rating: {pub.rating}</p>
              {/* <p>District: {pub.district_post_code}</p> */}
              <p><a href={pub.website_link} target="_blank" rel="noopener noreferrer">website</a></p>
              {/* <p>Offers: {pub.beverage_options ? 'Available' : 'No offers tracked yet'}</p> */}
          </div>
          ))}
      </div>
    </div>
  );
}

export default App;
