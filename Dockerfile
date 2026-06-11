FROM mambaorg/micromamba:1.5.8

WORKDIR /app

COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /app/environment.yml
RUN micromamba install -y -n base -f /app/environment.yml && micromamba clean --all --yes

COPY --chown=$MAMBA_USER:$MAMBA_USER . /app

EXPOSE 8501

CMD ["micromamba", "run", "-n", "base", "streamlit", "run", "ui/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
