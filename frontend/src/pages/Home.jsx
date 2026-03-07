import { useNavigate } from "react-router-dom"

export default function Home() {
    const navigate = useNavigate()

    const selectApp = () => {
        navigate("/login")
    }

    return (
        <div style={{
            height: '100vh',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            textAlign: 'center',
            padding: '20px'
        }}>
            <h1 style={{ fontSize: '4rem', marginBottom: '0' }}>SignalShift</h1>
            <p style={{ color: '#888', fontSize: '1.2rem', maxWidth: '600px', marginBottom: '50px' }}>
                Advanced Product Intelligence & Churn Prediction System.
            </p>

            <div className="glass-card" style={{ 
                maxWidth: '400px', 
                cursor: 'pointer',
                transition: 'transform 0.3s ease'
            }} onClick={selectApp}>
                <div style={{ 
                    height: '200px', 
                    background: 'url("https://images.unsplash.com/photo-1574375927938-d5a98e8ffe85?auto=format&fit=crop&w=400&q=80")',
                    backgroundSize: 'cover',
                    borderRadius: '8px',
                    marginBottom: '20px'
                }} />
                <h2 style={{ margin: '0' }}>Netflix Analysis</h2>
                <p style={{ color: '#666', fontSize: '14px', marginTop: '10px' }}>
                    Monitor sentiment, detect technical issues, and improve retention with ABSA technology.
                </p>
                <button className="btn-primary" style={{ width: '100%', marginTop: '20px' }}>
                    Enter Dashboard
                </button>
            </div>

            <p style={{ marginTop: '40px', fontSize: '12px', color: '#444' }}>
                SignalShift Research V2.0 | Powered by SignalShiftBERT
            </p>
        </div>
    )
}