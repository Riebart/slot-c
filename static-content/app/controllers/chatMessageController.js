myApp.controller('chatMessageCtrl', ['$scope', '$rootScope', '$resource', '$http', '$timeout', function ($scope, $rootScope, $resource, $http, $timeout) {

    // Hold the number of seconds until the file upload token expires.
    $scope.file_upload = '';
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
                $scope.file_upload = '';

                var fd = new FormData();
                for (var k in response.fields) {
                    fd.append(k, response.fields[k]);
                }
                //fd.append('Content-Type', document.getElementById("file-upload").files[0].type);
                fd.append('file', document.getElementById("file-upload").files[0]);
                $http({
                    method: 'POST',
                    url: response.url,
                    headers: { 'Content-Type': undefined },
                    transformRequest: angular.identity,
                    data: fd
                }).then(function success(response) { console.log('success'); console.log(response); },
                function failure(response) { console.log('failure'); console.log(response); }
                );

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

    $scope.FileCountdown = function () {
        var poll = function () {
            $timeout(function () {
                if ($scope.file_upload > 0) {
                    $scope.file_upload -= 1;
                    poll();
                }
            }, 1000);
        };
        poll();
    }

    $scope.chatMessageKeyPressed = function (keyEvent) {
        if ((keyEvent.which === 13) && (!$scope.posting)) {
            $scope.posting = true;
            var message_text = $scope.chatMessage;
            $scope.chatMessage = null;
            console.log('Sending Message: ' + $scope.chatMessage);

            // If this is the /file command
            if (message_text.substring(0, 5) == '/file') {
                $scope.file_upload = 'select';
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
