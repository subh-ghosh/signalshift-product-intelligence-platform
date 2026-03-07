import { useNavigate } from "react-router-dom"
import { useState } from "react"

export default function Login() {
    const navigate = useNavigate()

    const [email, setEmail] = useState("")
    const [password, setPassword] = useState("")
    const [error, setError] = useState("")

    const handleLogin = () => {
        const validEmail = "netflix_admin@signalshift.com"
        const validPassword = "admin123"

        if (email === validEmail && password === validPassword) {
            localStorage.setItem("token", "demo-user")
            navigate("/dashboard")
        } else {
            setError("Invalid credentials. Please contact IT.")
        }
    }

    return (
        <div style={{
            height: '100vh',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            background: 'url("https://images.unsplash.com/photo-1510511459019-5dee99c4859a?auto=format&fit=crop&w=1920&q=80")',
            backgroundSize: 'cover'
        }}>
            <div className="glass-card" style={{ width: '400px', padding: '40px' }}>
                <h2 style={{ fontSize: '24px', marginBottom: '10px' }}>Manager Access</h2>
                <p style={{ color: '#888', fontSize: '14px', marginBottom: '30px' }}>
                    Enter credentials to access private data intelligence.
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                    <input
                        type="text"
                        placeholder="Admin Email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        style={{
                            padding: '12px',
                            background: 'rgba(255,255,255,0.05)',
                            border: '1px solid rgba(255,255,255,0.2)',
                            borderRadius: '4px',
                            color: 'white'
                        }}
                    />

                    <input
                        type="password"
                        placeholder="Security Key"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        style={{
                            padding: '12px',
                            background: 'rgba(255,255,255,0.05)',
                            border: '1px solid rgba(255,255,255,0.2)',
                            borderRadius: '4px',
                            color: 'white'
                        }}
                    />

                    <button className="btn-primary" onClick={handleLogin}>
                        Authorize Session
                    </button>
                </div>

                {error && (
                    <p style={{ 
                        color: "#E50914", 
                        fontSize: '12px', 
                        marginTop: '20px',
                        background: 'rgba(229,9,20,0.1)',
                        padding: '10px',
                        borderRadius: '4px'
                    }}>
                        🚨 {error}
                    </p>
                )}
            </div>
        </div>
    )
}