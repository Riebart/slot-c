myApp.controller('chatMessageCtrl', ['$scope', '$rootScope', '$resource', '$http', '$timeout', function ($scope, $rootScope, $resource, $http, $timeout) {

    // Hold the number of seconds until the file upload token expires.
    $scope.file_upload = {};
    $scope.file_upload.status = 'idle';

    $scope.fileUpload = function () {
        if (document.getElementById("file-upload").files.length == 0) {
            return;
        }

        var message = {
            // encodeURIComponent() doesn't encode single quotes, which are a problem
            // for API Gateway.
            channel: $rootScope.channel,
            participant: $rootScope.userName,
            message: '/file ' + document.getElementById("file-upload").files[0].type + ' ' + document.getElementById("file-upload").files[0].name
        };
        console.log(message);

        $scope.MessagesResource.save(message, function (response) {
            if ((response.fields !== undefined) &&
                (response.fields.AWSAccessKeyId !== undefined)) {

                var fd = new FormData();
                for (var k in response.fields) {
                    fd.append(k, response.fields[k]);
                }
                fd.append('file', document.getElementById("file-upload").files[0]);

                $scope.file_upload.status = 'in_progress';
                $scope.file_upload.percent = 0;
                $scope.file_upload.rate = 0;
                $scope.file_upload.start = new Date;

                var xhr = new XMLHttpRequest;
                xhr.upload.onprogress = function (e) {
                    t = new Date;
                    percent = (100.0 * e.loaded) / e.total;
                    rate = 100.0 * e.loaded / (t - $scope.file_upload.start) / 1024;

                    // Truncate them to two decimal places
                    $scope.file_upload.percent = Math.round(100 * percent) / 100;
                    $scope.file_upload.rate = Math.round(100 * rate) / 100;
                };

                xhr.upload.onload = function (e) {
                    $scope.file_upload.status = 'success';
                };

                xhr.upload.onerror = function (e) {
                    $scope.file_upload.status = 'failure';
                };

                xhr.open('POST', response.url);
                xhr.send(fd);

                $rootScope.$emit('serverMessage', response.server_messages);
                $rootScope.$emit('eventMessageRefresh');
            }
        });
    };

    $rootScope.$on("chatting", function () {
        document.getElementById('chat-message-input').placeholder = "Enter a message and save humanity";
    });
    $rootScope.$on("not chatting", function () {
        document.getElementById('chat-message-input').value = null;
        document.getElementById('chat-message-input').placeholder = "Save your brains, enter your user name";
    });

    $scope.TalkersResource = $resource(API_ENDPOINT + "/participant" + "?Channel=" + DEFAULT_CHANNEL_NAME);
    $scope.MessagesResource = $resource(API_ENDPOINT + "/message");
    $scope.lastTalking = new Date;

    $rootScope.$on('channelChanged', function (event, new_channel) {
        $scope.TalkersResource = $resource(API_ENDPOINT + "/participant" + "?Channel=" + new_channel);
    });

    $scope.chatMessageKeyPressed = function (keyEvent) {
        if ((keyEvent.which === 13) && (!$scope.posting)) {
            $scope.posting = true;
            var message_text = $scope.chatMessage;
            $scope.chatMessage = null;
            console.log('Sending Message: ' + $scope.chatMessage);

            // If this is the /file command
            if ((message_text.substring(0, 5) == '/file') && 
                ($scope.file_upload.status != 'in_progress')) {
                $scope.file_upload.status = 'select';
                $scope.posting = false;
                return;
            }

            var message = {
                // encodeURIComponent() doesn't encode single quotes, which are a problem
                // for API Gateway.
                channel: $rootScope.channel,
                participant: $rootScope.userName,
                message: message_text
            };
            console.log(message);

            $scope.MessagesResource.save(message, function (response) {
                $scope.posting = false;
                document.getElementById("chat-message-input").focus();
                $rootScope.$emit('serverMessage', response.server_messages);
                $rootScope.$emit('eventMessageRefresh');
            });
        } else {
            var diff = Date.now() - $scope.lastTalking;
            console.log(diff);

            // send talking update at a maximum rate
            if (diff < 1000) {
                return;
            }

            var message = {
                channel: $rootScope.channel,
                participant: $rootScope.userName
            };

            console.log('Posting to talkers.');
            $scope.TalkersResource.save(message, function () {
                $scope.lastTalking = new Date;
            });
        }
    };

}]);
