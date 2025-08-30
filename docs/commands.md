flyctl deploy -c fly.listener.toml
fly logs -a backend-weathered-shadow-9057 -n | tail -30
fly secrets set ENV=PRODUCTION
fly status
fly machine start

in server: 
    cat .env
