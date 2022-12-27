In configuration file 
beehive3-cli/deploy/nginx/nginx-files/beehive-ssl-api.mylab.conf
update "minikube ip"

# build nginx image
docker image build --tag nivola/https-nginx -f Dockerfile.https.nginx .

# to delete nginx image
# docker container prune
# docker image rmi nivola/https-nginx

# to run bash nginx
docker run -it nivola/https-nginx bash
# to run nginx (in minikube network)
docker network ls | grep minikube
docker run --network 172f04f59d8f --name tmp-nginx-container -d nivola/https-nginx
docker run --network nivolanet --name tmp-nginx-container -d nivola/https-nginx

# log nginx
docker exec -it tmp-nginx-container tail -f /var/log/nginx/beehive.api.test.access.log
docker exec -it tmp-nginx-container tail -f /var/log/nginx/beehive.api.test.error.log
docker exec -it tmp-nginx-container tail -f /var/log/nginx/access.log
docker exec -it tmp-nginx-container tail -f /var/log/nginx/error.log
docker logs tmp-nginx-container (access.log e error.log dovrebbero essere rediretti qui)

# to stop nginx
docker container stop tmp-nginx-container
docker container prune

# to find docker nginx IP address (for update CLI configuration endpoints)
docker ps | grep tmp-nginx-container
docker inspect d852d389268f | grep "IPAddress"

# test using CLI (running in minikube network)
curl -k https://192.168.49.4
    ...
    <title>Welcome to nginx!</title>

curl -k https://192.168.49.4/mylab/v1.0/server/ping
    {"name":"beehive","id":"auth","hostname":...

