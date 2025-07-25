import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';

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

function Carousel({ cities, selectedCity, onSelect }) {
  const [displayedCities, setDisplayedCities] = useState([]);

  useEffect(() => {
    const allCities = [
      ...cities,
      'leeds1', 'leeds2', 'london1', 'london2',
    ];
    const filteredCities = allCities.filter(city => city !== selectedCity);
    const finalCities = [...new Set(filteredCities)].slice(0, 8); // Limit to 8 for 1x8
    setDisplayedCities(finalCities);
  }, [cities, selectedCity]);

  return (
    <div className="relative w-full h-[150px]">
      <div className="absolute inset-0">
        {/* Fixed gradient container */}
        <div className="absolute top-0 left-0 w-16 h-full bg-gradient-to-r from-teal-950 to-transparent pointer-events-none z-10"></div>
        <div className="absolute top-0 right-0 w-16 h-full bg-gradient-to-l from-teal-950 to-transparent pointer-events-none z-10"></div>
      </div>
      <div className="relative h-full overflow-x-auto overflow-y-hidden">
        <div className="flex space-x-4 pb-4" style={{ width: `${displayedCities.length * 150}px` }}>
          {displayedCities.map((city) => (
            <div className="relative flex-shrink-0" key={city}>
              <div className="w-[150px] h-[150px] overflow-hidden">
                <motion.iframe
                  src={`/static/preprocessing/${city}_heatmap.html`}
                  alt={`${city} map`}
                  className="object-cover"
                  style={{ width: '150px', height: '150px' }}
                />
                <motion.div
                  className="absolute top-0 left-0 w-[150px] h-[150px] flex items-center justify-center bg-black bg-opacity-0 hover:bg-opacity-30 transition-opacity duration-200 text-white text-lg"
                  initial={{ opacity: 0 }}
                  whileHover={{ opacity: 1 }}
                  onClick={() => onSelect(city)}
                >
                  {cityNames[city] || city}
                </motion.div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Carousel;