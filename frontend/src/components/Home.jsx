import { useEffect, useState } from 'react';
import ThumbnailGrid from './ThumbnailGrid.jsx';
import Carousel from './Carousel.jsx';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';

function Home() {
  const navigate = useNavigate();
  const [cities, setCities] = useState([]);
  const [selectedCity, setSelectedCity] = useState(null);
  const [isMapVisible, setIsMapVisible] = useState(false);
  const [isClosing, setIsClosing] = useState(false);

  const cityNames = {
    leeds1: "Leeds – Train Station",
    leeds2: "Leeds – Beeston",
    leeds3: "Leeds – Stourton",
    leeds4: "Leeds – Burley",
    london1: "London – Charing Cross",
    london2: "London – Islington",
    london3: "London – Hackney",
    london4: "London – Islington",
    london5: "London – Canning Town",
    london6: "London – Seven Sisters",
    london7: "London – Willesden",
  };

  const cityDetails = {
    leeds1: "Specific text 1",
    leeds2: "Specific text 2",
    leeds3: "Specific text 3",
    leeds4: "Specific text 4",
    london1: "Specific text 5",
    london2: "Specific text 6",
    london3: "Specific text 7",
    london4: "Specific text 8",
    london5: "Specific text 9",
    london6: "Specific text 10",
    london7: "Specific text 11",
  };


  useEffect(() => {
    fetch('http://localhost:8000/cities')
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
      })
      .then((data) => setCities(data.cities || []))
      .catch((err) => console.error('Error fetching cities:', err.message));
  }, []);

  const handleSelect = (city) => {
    if (selectedCity === city) {
      setIsClosing(true);
      setIsMapVisible(false);
    } else {
      setSelectedCity(city);
      setIsMapVisible(true);
      setIsClosing(false);
      navigate(`/map/${city}`);
    }
  };

  const MapView = ({ city, onToggle }) => {
    return (
      <motion.div
        className="w-full h-full relative"
        initial={{ scale: 0.25, width: '200px', height: '200px' }}
        animate={{ scale: 1, width: '100%', height: '100%' }}
        exit={{ scale: 0.25, width: '200px', height: '200px' }}
        style={{ transformOrigin: 'center' }}
        transition={{ duration: 0.9 }} // Ensure transition applies to exit
      >
        <iframe
          src={`/static/preprocessing/${city}_heatmap.html`}
          className="w-full h-full border-none"
          title={`${city} heatmap`}
        />
        <motion.div
          className="absolute top-2 right-2 rounded-full p-1 cursor-pointer text-black bg-white bg-opacity-75"
          onClick={onToggle}
          whileHover={{ scale: 1.1 }}
        >
          🔍
        </motion.div>
      </motion.div>
    );
  };

  return (
    <div className="flex h-screen bg-teal-950 text-white">
      <div className="w-[40%] p-4">
        <h1 className="text-3xl font-bold">Sunday Evening - How far can you travel by public transport?</h1>
        <p className="mt-4">
          Select a map to view travel times by public transport from various neighbourhoods in Leeds and London.
        </p>
      </div>
      <div className="w-[60%] p-4">
        <ThumbnailGrid cities={cities} onSelect={handleSelect} />
      </div>
      {selectedCity && (
        <AnimatePresence
          onExitComplete={() => {
            if (isClosing) {
              setSelectedCity(null);
              navigate('/');
            }
          }}
        >
          {isMapVisible && selectedCity && (
            <motion.div
              key={selectedCity} // Ensures re-mount for exit animation
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-teal-950 flex"
              transition={{ duration: 0.5 }}
              >
              <div className="w-[60%] p-4">
                <MapView city={selectedCity} onToggle={() => handleSelect(selectedCity)} />
              </div>
              <div className="w-[40%] p-4 flex flex-col">
                <div className="flex-1 p-4">
                  <h2 className="text-xl font-bold">{cityNames[selectedCity]}</h2>
                  <p>{cityDetails[selectedCity] || "No detailed information available."}</p>
                </div>
                <div className="flex-1 mt-4">
                  <Carousel cities={cities} selectedCity={selectedCity} onSelect={handleSelect} />
                </div>
              </div>
          </motion.div>
          )}
        </AnimatePresence>
      )}
    </div>
  );
}

export default Home;