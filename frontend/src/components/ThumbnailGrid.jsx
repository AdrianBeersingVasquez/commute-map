import { motion } from 'framer-motion';

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

function ThumbnailGrid({ cities, onSelect }) {
  return (
    <div className="grid grid-cols-3 gap-4">
      {cities.map((city) => (
        <div className="relative" key={city}>
          <div className="w-[200px] h-[200px] overflow-hidden">
            <motion.iframe
              src={`/static/preprocessing/${city}_heatmap.html`}
              alt={`${city} map`}
              className="object-cover"
              style={{ width: '200px', height: '200px' }}
            />
            <motion.div
              className="absolute top-0 left-0 w-[200px] h-[200px] flex items-center justify-center bg-black bg-opacity-0 hover:bg-opacity-30 transition-opacity duration-200 text-white text-lg"
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
  );
}

export default ThumbnailGrid;