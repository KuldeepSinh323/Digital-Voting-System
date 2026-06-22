## Digital Voting App

A simple distributed application running across multiple Docker containers.

## Getting started

Download [Docker Desktop](https://www.docker.com/products/docker-desktop) for Mac or Windows. [Docker Compose](https://docs.docker.com/compose) will be automatically installed. On Linux, make sure you have the latest version of [Compose](https://docs.docker.com/compose/install/).

This solution uses Python, Node.js, .NET, with Redis for messaging and Postgres for storage.

Run in this directory to build and run the app:

```shell
docker compose up
```

The `vote` app will be running at [http://localhost:8080](http://localhost:8080), and the `results` will be at [http://localhost:8081](http://localhost:8081).

Alternately, if you want to run it on a [Docker Swarm](https://docs.docker.com/engine/swarm/), first make sure you have a swarm. If you don't, run:

```shell
docker swarm init
```

Once you have your swarm, in this directory run:

```shell
docker stack deploy --compose-file docker-stack.yml vote
```

## Run the app in Kubernetes

The folder k8s-specifications contains the YAML specifications of the Voting App's services.

Run the following command to create the deployments and services. Note it will create these resources in your current namespace (`default` if you haven't changed it.)

```shell
kubectl create -f k8s-specifications/
```

The `vote` web app is then available on port 31000 on each host of the cluster, the `result` web app is available on port 31001.

To remove them, run:

```shell
kubectl delete -f k8s-specifications/
```

## Architecture

## DATABASE DESIGN

<img width="902" height="519" alt="image" src="https://github.com/user-attachments/assets/eef7bbb1-8496-4674-9ff6-f70af6020428" />

## SYSTEM DESIGN & METHODOLOGY

<img width="883" height="853" alt="image" src="https://github.com/user-attachments/assets/33e52182-eac2-4358-abde-4923d7f94120" />

* A front-end web app in [Python](/vote) which lets you vote between two options
* A [Redis](https://hub.docker.com/_/redis/) which collects new votes
* A [.NET](/worker/) worker which consumes votes and stores them in…
* A [Postgres](https://hub.docker.com/_/postgres/) database backed by a Docker volume
* A [Node.js](/result) web app which shows the results of the voting in real time

## Notes

The voting application only accepts one vote per client browser. It does not register additional votes if a vote has already been submitted from a client.

This isn't an example of a properly architected perfectly designed distributed app... it's just a simple
example of the various types of pieces and languages you might see (queues, persistent data, etc), and how to
deal with them in Docker at a basic level.


## Application Preview


## Home page

•	This Page gives Details Of features of Web Application   

<img width="963" height="530" alt="image" src="https://github.com/user-attachments/assets/ade5aeba-7a1d-4356-b27c-bdc13d8f1de2" />

 ## Registration Page
•	Here New user can create user name and password to access this application 

•	If user name is Already existing then Its shows “user already exists” pop-up

•	All new registration user assigned Default Normal user role
<img width="963" height="599" alt="image" src="https://github.com/user-attachments/assets/45ec33e9-c4b9-4e6d-b6e4-ca3035bae14e" />

## User Login Page

•	Here only registered user can login to Applicaion 

•	If User password is Wrong, user does not registered than it can not able to login 
<img width="903" height="507" alt="image" src="https://github.com/user-attachments/assets/d47aa88a-60cb-46de-bc7b-98b8b7f1c393" />

## Voting Interface 

•	Voting page display username with voting option details 

•	One user can vote/ poll for only one option

•	If one option is selected then another option is disabled.

 <img width="903" height="536" alt="image" src="https://github.com/user-attachments/assets/efdb5c4d-c607-4ce5-ad99-77b5b4c66c1f" />

 ## About and Dashboard 

•	Its give information about Digital Voting System

<img width="923" height="569" alt="image" src="https://github.com/user-attachments/assets/66f4108b-bdf9-4414-9fb8-26f5b02d64aa" />

<img width="931" height="559" alt="image" src="https://github.com/user-attachments/assets/3fb1b846-c70a-4090-8ba0-faa4bda1500d" />

## Results 

•	The live voting results displayed on the dashboard

•	Admin User only can view or access this web page 

•	Result of voting Demonstrates with different graphs 

•	Its also display Voting details like Voter id , vote , also date and time

<img width="902" height="534" alt="image" src="https://github.com/user-attachments/assets/d80c4186-b2d3-4445-aad7-53938bc0ed91" />

<img width="902" height="507" alt="image" src="https://github.com/user-attachments/assets/45fae7dd-67d6-436e-b749-5a9a3ee09641" />

## Admin Controls 

•	User management and voting creation only accessed by Admin users

•	This dashboard gives all details as Total users, username ,role ,actions.

•	Admin can create new voting Option at Voting creation Page 

<img width="978" height="562" alt="image" src="https://github.com/user-attachments/assets/a377c46a-9d5f-4a36-ad6e-18733e9aad7c" />

<img width="978" height="561" alt="image" src="https://github.com/user-attachments/assets/eb287a6b-302f-48ff-a033-6d87a8e2db17" />





