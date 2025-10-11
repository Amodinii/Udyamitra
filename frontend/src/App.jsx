<<<<<<< HEAD
import './App.css'

// importing the components
import ChatbotWidget from './components/ChatbotWidget'

function App() {
  return (
    <>
      <p> Sample text for seeing purpose. </p>
      <ChatbotWidget />
    </>
  )
}

export default App
=======
import Chatbot from '@/components/Chatbot';

function App() {

  return (
    <div className='flex flex-col min-h-full w-full max-w-3xl mx-auto px-4'>
      <header className='sticky top-0 shrink-0 z-20 bg-[#1E1E1E]'>
        <div className='flex flex-col h-full w-full gap-1 pt-4 pb-2'>
        </div>
      </header>
      <Chatbot />
    </div>
  );
}

export default App;
>>>>>>> Amodini
