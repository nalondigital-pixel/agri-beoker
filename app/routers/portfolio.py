from fastapi import APIRouter
from fastapi.responses import HTMLResponse


router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


def portfolio_page():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Darlington Mponda | Portfolio</title>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />

        <style>
            :root {
                --bg: #ffffff;
                --text: #171717;
                --muted: #666666;
                --line: #e9e9e9;
                --card: #ffffff;
                --soft: #f7f7f8;
                --blue: #2563eb;
                --blue-dark: #1d4ed8;
                --green: #16a34a;
                --shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
                --radius: 26px;
            }

            body.dark {
                --bg: #0b1020;
                --text: #f8fafc;
                --muted: #a7b0c0;
                --line: rgba(255,255,255,0.10);
                --card: rgba(255,255,255,0.06);
                --soft: rgba(255,255,255,0.08);
                --shadow: 0 18px 50px rgba(0,0,0,0.35);
            }

            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            html {
                scroll-behavior: smooth;
            }

            body {
                font-family: "Segoe UI", Arial, sans-serif;
                background: var(--bg);
                color: var(--text);
                transition: background 0.3s ease, color 0.3s ease;
            }

            a {
                color: inherit;
                text-decoration: none;
            }

            .nav-wrap {
                position: sticky;
                top: 0;
                z-index: 50;
                background: rgba(255,255,255,0.82);
                backdrop-filter: blur(18px);
                border-bottom: 1px solid var(--line);
            }

            body.dark .nav-wrap {
                background: rgba(11,16,32,0.82);
            }

            .nav {
                max-width: 1120px;
                margin: 0 auto;
                padding: 18px 24px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 20px;
            }

            .signature {
                font-family: "Segoe Print", "Comic Sans MS", cursive;
                font-size: 24px;
                font-weight: 700;
                letter-spacing: -1px;
            }

            .nav-links {
                display: flex;
                align-items: center;
                gap: 30px;
                color: var(--muted);
                font-size: 15px;
            }

            .nav-links a {
                position: relative;
                padding: 8px 0;
                transition: color 0.25s ease;
            }

            .nav-links a:hover {
                color: var(--text);
            }

            .nav-links a::after {
                content: "";
                position: absolute;
                left: 0;
                bottom: 0;
                height: 2px;
                width: 0;
                background: var(--blue);
                transition: width 0.25s ease;
            }

            .nav-links a:hover::after {
                width: 100%;
            }

            .nav-actions {
                display: flex;
                align-items: center;
                gap: 10px;
            }

            .theme-btn {
                width: 40px;
                height: 40px;
                border-radius: 999px;
                border: 1px solid var(--line);
                background: var(--soft);
                color: var(--text);
                cursor: pointer;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                transition: transform 0.25s ease;
            }

            .theme-btn:hover {
                transform: translateY(-2px);
            }

            .quote-btn {
                padding: 12px 22px;
                border-radius: 999px;
                border: 1px solid var(--line);
                background: var(--card);
                font-weight: 600;
                color: var(--text);
                transition: all 0.25s ease;
            }

            .quote-btn:hover {
                transform: translateY(-2px);
                box-shadow: var(--shadow);
            }

            .container {
                max-width: 1120px;
                margin: 0 auto;
                padding: 0 24px;
            }

            section {
                padding: 80px 0;
            }

            .hero {
                min-height: calc(100vh - 82px);
                display: grid;
                grid-template-columns: 1.25fr 0.9fr;
                gap: 70px;
                align-items: center;
            }

            .intro {
                font-family: "Segoe Print", "Comic Sans MS", cursive;
                color: var(--blue);
                font-size: 20px;
                margin-bottom: 18px;
                transform: rotate(-4deg);
                display: inline-block;
            }

            .hero-title {
                font-family: "Segoe Print", "Comic Sans MS", cursive;
                font-size: clamp(58px, 8vw, 105px);
                line-height: 0.95;
                letter-spacing: -5px;
                margin-bottom: 24px;
            }

            .role {
                font-size: 19px;
                color: var(--muted);
                font-weight: 600;
                margin-bottom: 24px;
            }

            .hero-copy {
                max-width: 580px;
                color: var(--muted);
                font-size: 17px;
                line-height: 1.8;
            }

            .hero-copy strong {
                color: var(--text);
            }

            .actions {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                margin-top: 34px;
            }

            .btn {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 9px;
                padding: 16px 26px;
                border-radius: 999px;
                font-weight: 700;
                border: 1px solid var(--line);
                background: var(--card);
                transition: all 0.25s ease;
            }

            .btn.primary {
                background: var(--blue);
                color: white;
                border-color: var(--blue);
            }

            .btn:hover {
                transform: translateY(-4px);
                box-shadow: var(--shadow);
            }

            .profile-side {
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .profile-card {
                width: 330px;
                height: 330px;
                border-radius: 30px;
                border: 1px solid var(--line);
                box-shadow: var(--shadow);
                overflow: hidden;
                background: var(--soft);
                position: relative;
            }

            .profile-card img {
                width: 100%;
                height: 100%;
                object-fit: cover;
                object-position: center top;
                transform: scale(1.13);
                transform-origin: top center;
                display: block;
            }

            .socials {
                display: flex;
                gap: 12px;
                margin-top: 34px;
            }

            .socials a {
                width: 42px;
                height: 42px;
                border-radius: 999px;
                background: var(--soft);
                border: 1px solid var(--line);
                display: inline-flex;
                align-items: center;
                justify-content: center;
                color: var(--muted);
                font-weight: 800;
                transition: all 0.25s ease;
            }

            .socials a:hover {
                transform: translateY(-4px);
                color: var(--blue);
                box-shadow: var(--shadow);
            }

            .section-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 80px;
                align-items: start;
            }

            .section-label {
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 4px;
                color: #9ca3af;
                font-weight: 900;
                margin-bottom: 24px;
            }

            .section-title {
                font-family: "Segoe Print", "Comic Sans MS", cursive;
                font-size: clamp(40px, 6vw, 66px);
                line-height: 1.05;
                letter-spacing: -3px;
                margin-bottom: 24px;
            }

            .text-block p {
                color: var(--muted);
                font-size: 17px;
                line-height: 1.9;
                margin-bottom: 26px;
            }

            .text-block strong {
                color: var(--text);
            }

            .pill-wrap {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
            }

            .pill {
                padding: 12px 18px;
                border-radius: 999px;
                border: 1px solid var(--line);
                background: var(--card);
                color: var(--text);
                font-size: 14px;
                transition: all 0.25s ease;
            }

            .pill:hover {
                transform: translateY(-3px);
                box-shadow: var(--shadow);
            }

            .projects {
                background: var(--soft);
                border-top: 1px solid var(--line);
                border-bottom: 1px solid var(--line);
            }

            body.dark .projects {
                background: rgba(255,255,255,0.03);
            }

            .work-header {
                display: flex;
                justify-content: space-between;
                gap: 30px;
                align-items: end;
                margin-bottom: 34px;
            }

            .work-header p {
                max-width: 520px;
                color: var(--muted);
                line-height: 1.8;
            }

            .project-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 22px;
            }

            .project-card {
                background: var(--card);
                border: 1px solid var(--line);
                border-radius: var(--radius);
                padding: 28px;
                box-shadow: var(--shadow);
                transition: all 0.3s ease;
            }

            .project-card:hover {
                transform: translateY(-8px);
            }

            .project-card h3 {
                font-size: 22px;
                margin-bottom: 12px;
            }

            .project-card p {
                color: var(--muted);
                line-height: 1.75;
                font-size: 15px;
            }

            .tag-row {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin: 20px 0;
            }

            .tag {
                padding: 8px 11px;
                border-radius: 999px;
                background: var(--soft);
                border: 1px solid var(--line);
                font-size: 12px;
                font-weight: 700;
                color: var(--muted);
            }

            .project-links {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin-top: 22px;
            }

            .project-links a {
                font-size: 13px;
                font-weight: 800;
                color: white;
                background: var(--blue);
                padding: 10px 14px;
                border-radius: 999px;
                transition: all 0.25s ease;
            }

            .project-links a.secondary {
                background: var(--soft);
                color: var(--text);
                border: 1px solid var(--line);
            }

            .project-links a.green {
                background: var(--green);
                color: white;
            }

            .project-links a:hover {
                transform: translateY(-3px);
            }

            .contact {
                display: grid;
                grid-template-columns: 0.9fr 1.2fr;
                gap: 70px;
                align-items: start;
            }

            .contact-list {
                display: grid;
                gap: 20px;
                margin-top: 34px;
            }

            .contact-item {
                display: grid;
                grid-template-columns: 52px 1fr;
                gap: 16px;
                align-items: center;
            }

            .contact-icon {
                width: 52px;
                height: 52px;
                border-radius: 16px;
                border: 1px solid var(--line);
                background: var(--card);
                display: flex;
                align-items: center;
                justify-content: center;
                color: var(--blue);
                font-weight: 900;
                box-shadow: var(--shadow);
            }

            .contact-item small {
                display: block;
                text-transform: uppercase;
                letter-spacing: 2px;
                color: #9ca3af;
                font-weight: 800;
                margin-bottom: 6px;
            }

            .contact-item span {
                color: var(--text);
            }

            .contact-form {
                background: var(--card);
                border: 1px solid var(--line);
                border-radius: var(--radius);
                padding: 34px;
                box-shadow: var(--shadow);
            }

            .form-row {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 18px;
            }

            label {
                display: block;
                font-size: 14px;
                margin-bottom: 10px;
                color: var(--text);
            }

            input,
            textarea {
                width: 100%;
                padding: 15px 18px;
                border-radius: 12px;
                border: 1px solid var(--line);
                background: var(--bg);
                color: var(--text);
                font-size: 15px;
                outline: none;
                margin-bottom: 22px;
                transition: all 0.25s ease;
            }

            input:focus,
            textarea:focus {
                border-color: var(--blue);
                box-shadow: 0 0 0 4px rgba(37,99,235,0.12);
            }

            textarea {
                min-height: 140px;
                resize: vertical;
            }

            .submit {
                width: 100%;
                border: none;
                background: var(--blue);
                color: white;
                padding: 16px;
                border-radius: 999px;
                font-weight: 800;
                cursor: pointer;
                transition: all 0.25s ease;
            }

            .submit:hover {
                background: var(--blue-dark);
                transform: translateY(-3px);
                box-shadow: var(--shadow);
            }

            .footer {
                padding: 30px 24px;
                text-align: center;
                color: var(--muted);
                border-top: 1px solid var(--line);
            }

            @media (max-width: 900px) {
                .hero,
                .section-grid,
                .contact {
                    grid-template-columns: 1fr;
                    gap: 45px;
                }

                .project-grid {
                    grid-template-columns: 1fr;
                }

                .work-header {
                    display: block;
                }

                .profile-side {
                    justify-content: flex-start;
                }
            }

            @media (max-width: 680px) {
                .nav {
                    flex-direction: column;
                    align-items: flex-start;
                }

                .nav-links {
                    gap: 18px;
                    flex-wrap: wrap;
                }

                .nav-actions {
                    width: 100%;
                    justify-content: space-between;
                }

                section {
                    padding: 58px 0;
                }

                .hero-title {
                    font-size: 64px;
                }

                .profile-card {
                    width: 100%;
                    max-width: 330px;
                }

                .form-row {
                    grid-template-columns: 1fr;
                    gap: 0;
                }
            }
        </style>
    </head>

    <body>
        <div class="nav-wrap">
            <nav class="nav">
                <a class="signature" href="#home">Darlington M.</a>

                <div class="nav-links">
                    <a href="#home">Home</a>
                    <a href="#about">About</a>
                    <a href="#work">Work</a>
                    <a href="#contact">Contact</a>
                </div>

                <div class="nav-actions">
                    <button class="theme-btn" onclick="toggleTheme()" aria-label="Toggle dark mode">◐</button>
                    <a class="quote-btn" href="#contact">Get a Quote</a>
                </div>
            </nav>
        </div>

        <main>
            <section class="container hero" id="home">
                <div>
                    <span class="intro">Hi, I'm</span>
                    <h1 class="hero-title">Darlington<br>Mponda</h1>
                    <div class="role">Software & AI Developer</div>

                    <p class="hero-copy">
                        Computer Science graduate from <strong>Cavendish University Zambia</strong>,
                        based in <strong>Brackenfell, Cape Town</strong>. I build AI-powered systems,
                        modern web apps, dashboards, automation tools, and security-aware software
                        for real-world problems.
                    </p>

                    <div class="actions">
                        <a class="btn primary" href="#work">See my work</a>
                        <a class="btn" href="#contact">Get a quote</a>
                        <a class="btn" href="/static/darlington-mponda-cv.pdf" download>Download CV</a>
                    </div>

                    <div class="socials">
                        <a href="https://github.com/nalondigital-pixel" target="_blank">GH</a>
                        <a href="https://www.linkedin.com/" target="_blank">in</a>
                        <a href="mailto:nalondigital@gmail.com">@</a>
                    </div>
                </div>

                <div class="profile-side">
                    <div class="profile-card">
                        <img src="/static/profile.jpg" alt="Darlington Mponda profile photo" />
                    </div>
                </div>
            </section>

            <section class="container" id="about">
                <div class="section-grid">
                    <div class="text-block">
                        <p>
                            I studied <strong>Computer Science at Cavendish University Zambia</strong>,
                            where I developed a strong foundation in software development, problem solving,
                            databases, and systems thinking.
                        </p>

                        <p>
                            Today I work as a <strong>freelance software and AI developer</strong>,
                            building practical systems for small businesses, startups, and real-world
                            workflows. My work includes AI-powered marketplaces, admin dashboards,
                            booking systems, attendance systems, and automation tools.
                        </p>

                        <p>
                            I also approach projects with a security mindset. I test my own applications,
                            add security headers, validate user input, rate-limit sensitive endpoints,
                            and document findings in a SOC/security analyst style.
                        </p>
                    </div>

                    <div>
                        <div class="section-label">What I work with</div>

                        <div class="pill-wrap">
                            <span class="pill">Python</span>
                            <span class="pill">JavaScript</span>
                            <span class="pill">React JS</span>
                            <span class="pill">HTML & CSS</span>
                            <span class="pill">FastAPI</span>
                            <span class="pill">Django</span>
                            <span class="pill">SQL</span>
                            <span class="pill">Supabase</span>
                            <span class="pill">PostgreSQL</span>
                            <span class="pill">Gemini AI</span>
                            <span class="pill">OpenAI APIs</span>
                            <span class="pill">Claude AI</span>
                            <span class="pill">Docker</span>
                            <span class="pill">Linux / Nginx</span>
                            <span class="pill">Git & GitHub</span>
                            <span class="pill">Render</span>
                            <span class="pill">Vercel</span>
                            <span class="pill">WordPress</span>
                            <span class="pill">Bandit</span>
                            <span class="pill">pip-audit</span>
                            <span class="pill">OWASP Basics</span>
                        </div>
                    </div>
                </div>
            </section>

            <section class="projects" id="work">
                <div class="container">
                    <div class="work-header">
                        <div>
                            <div class="section-label">Things I've built</div>
                            <h2 class="section-title">Selected work</h2>
                        </div>

                        <p>
                            A mix of full-stack web apps, AI systems, dashboards, booking systems,
                            and security-focused project work.
                        </p>
                    </div>

                    <div class="project-grid">
                        <article class="project-card">
                            <h3>Agri Broker</h3>
                            <p>
                                AI-powered agriculture marketplace connecting farmers, buyers,
                                traders, and transporters.
                            </p>

                            <div class="tag-row">
                                <span class="tag">FastAPI</span>
                                <span class="tag">Supabase</span>
                                <span class="tag">Gemini AI</span>
                                <span class="tag">Render</span>
                                <span class="tag">Security</span>
                            </div>

                            <p>
                                Includes seller listings, buyer requests, transporter registration,
                                an AI chatbot, modern SaaS UI, and OWASP-style security hardening.
                            </p>

                            <div class="project-links">
                                <a href="/web" target="_blank">Live Demo</a>
                                <a class="secondary" href="/web/case-study" target="_blank">Case Study</a>
                                <a class="secondary" href="https://github.com/nalondigital-pixel/agri-beoker" target="_blank">GitHub</a>
                            </div>
                        </article>

                        <article class="project-card">
                            <h3>Attendance Management System</h3>
                            <p>
                                A full-stack employee attendance and staff management system built for
                                tracking employees, daily attendance, clock-in and clock-out records,
                                and admin operations.
                            </p>

                            <div class="tag-row">
                                <span class="tag">Python</span>
                                <span class="tag">Django</span>
                                <span class="tag">SQLite</span>
                                <span class="tag">Admin Dashboard</span>
                                <span class="tag">CRUD</span>
                                <span class="tag">Web App</span>
                            </div>

                            <p>
                                Includes employee records, department and position tracking,
                                attendance logs, salary information, status management, and admin
                                actions for marking clock-in and clock-out times.
                            </p>

                            <div class="project-links">
                                <a href="#contact">Request Demo</a>
                                <a class="secondary" href="#" target="_blank">GitHub Coming Soon</a>
                            </div>
                        </article>

                        <article class="project-card">
                            <h3>Hydro Booking App</h3>
                            <p>
                                A modern appointment booking website built for service-based businesses
                                to receive booking requests and manage customer interest online.
                            </p>

                            <div class="tag-row">
                                <span class="tag">React</span>
                                <span class="tag">JavaScript</span>
                                <span class="tag">Responsive UI</span>
                                <span class="tag">Vercel</span>
                                <span class="tag">Booking System</span>
                            </div>

                            <p>
                                Provides a clean customer-facing booking flow, responsive design,
                                service presentation, and a professional online presence for
                                appointment-based work.
                            </p>

                            <div class="project-links">
                                <a href="https://hydrofrontend.vercel.app/" target="_blank">Live Demo</a>
                                <a class="secondary" href="#" target="_blank">GitHub Coming Soon</a>
                            </div>
                        </article>
                    </div>
                </div>
            </section>

            <section class="container" id="contact">
                <h2 class="section-title">Let's build<br>something together</h2>
                <p class="hero-copy">
                    Whether it's a website, an AI system, a dashboard, automation, booking system,
                    attendance system, or a security review, my inbox is open.
                </p>

                <div class="contact">
                    <div>
                        <div class="contact-list">
                            <div class="contact-item">
                                <div class="contact-icon">@</div>
                                <div>
                                    <small>Email</small>
                                    <span>nalondigital@gmail.com</span>
                                </div>
                            </div>

                            <div class="contact-item">
                                <div class="contact-icon">GH</div>
                                <div>
                                    <small>GitHub</small>
                                    <span>github.com/nalondigital-pixel</span>
                                </div>
                            </div>

                            <div class="contact-item">
                                <div class="contact-icon">SA</div>
                                <div>
                                    <small>Location</small>
                                    <span>Brackenfell, Cape Town</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <form class="contact-form" action="mailto:nalondigital@gmail.com" method="post" enctype="text/plain">
                        <div class="form-row">
                            <div>
                                <label>Name</label>
                                <input name="name" placeholder="Your name" required />
                            </div>

                            <div>
                                <label>Email</label>
                                <input name="email" type="email" placeholder="your@email.com" required />
                            </div>
                        </div>

                        <label>Message</label>
                        <textarea name="message" placeholder="Tell me about your project or request a demo..." required></textarea>

                        <button class="submit" type="submit">Send it</button>
                    </form>
                </div>
            </section>
        </main>

        <footer class="footer">
            Built by Darlington Mponda — Software & AI Developer
        </footer>

        <script>
            function toggleTheme() {
                document.body.classList.toggle("dark");

                if (document.body.classList.contains("dark")) {
                    localStorage.setItem("theme", "dark");
                } else {
                    localStorage.setItem("theme", "light");
                }
            }

            if (localStorage.getItem("theme") === "dark") {
                document.body.classList.add("dark");
            }
        </script>
    </body>
    </html>
    """


@router.get("/")
def show_portfolio():
    return HTMLResponse(portfolio_page())