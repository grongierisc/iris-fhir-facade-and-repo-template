ARG IMAGE=containers.intersystems.com/intersystems/irishealth-community:latest-em
FROM $IMAGE 

USER root

# Update package and install sudo
RUN apt-get update && apt-get install -y \
	git \
	vim \
	sudo && \
	/bin/echo -e ${ISC_PACKAGE_MGRUSER}\\tALL=\(ALL\)\\tNOPASSWD: ALL >> /etc/sudoers && \
	sudo -u ${ISC_PACKAGE_MGRUSER} sudo echo enabled passwordless sudo-ing for ${ISC_PACKAGE_MGRUSER}

# Create local folder for the application
RUN mkdir -p /irisdev/app
RUN chown ${ISC_PACKAGE_MGRUSER}:${ISC_PACKAGE_IRISGROUP} /irisdev/app
# Change back the user to irisowner
USER ${ISC_PACKAGE_MGRUSER}

## Python stuff
ENV IRISUSERNAME="SuperUser"
ENV IRISPASSWORD="SYS"
ENV IRISNAMESPACE="EAI"

ENV PYTHON_PATH=/usr/irissys/bin/
ENV LD_LIBRARY_PATH=${ISC_PACKAGE_INSTALLDIR}/bin
ENV PATH="/home/irisowner/.local/bin:/usr/irissys/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/irisowner/bin"

# Copy the source code
COPY --chown=${ISC_PACKAGE_MGRUSER}:${ISC_PACKAGE_IRISGROUP} . /irisdev/app/

# Copy key file
# COPY key/iris.key /usr/irissys/mgr/iris.key

# Install the requirements
RUN pip3 install -r /irisdev/app/requirements.txt --break-system-packages


RUN cd /irisdev/app/src/FHIRSERVER/java/ && \
	mkdir -p /usr/irissys/lib/java && \
	wget https://github.com/hapifhir/org.hl7.fhir.core/releases/download/6.5.27/validator_cli.jar -O /usr/irissys/lib/java/validator_cli.jar && \
	javac /irisdev/app/src/FHIRSERVER/java/Iris/JavaValidatorFacade.java -classpath /usr/irissys/lib/java/validator_cli.jar -d /usr/irissys/lib/java

ENTRYPOINT [ "/tini", "--", "/irisdev/app/docker-entrypoint.sh" ]

CMD [ "iris" ]