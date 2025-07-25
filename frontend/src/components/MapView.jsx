import { motion } from 'framer-motion';
import { useParams } from 'react-router-dom';

function MapView() {
  const { city } = useParams();

  if (!city) {
    return <div>Error: No city parameter provided.</div>;
  }

  return (
    <motion.div
      className="w-3/4 h-3/4 bg-white p-4 relative"
      initial={{ scale: 0.5 }}
      animate={{ scale: 1 }}
      exit={{ scale: 0.5 }}
    >
      <iframe
        src={`/static/preprocessing/${city}_heatmap.html`}
        className="w-full h-full border-none"
        title={`${city} heatmap`}
      />
      <motion.div
        className="absolute top-2 right-2 bg-white rounded-full p-1 cursor-pointer text-black"
        onClick={() => window.history.back()} // Collapse by navigating back
        whileHover={{ scale: 1.1 }}
      >
        🔍
      </motion.div>
    </motion.div>
  );
}

export default MapView;